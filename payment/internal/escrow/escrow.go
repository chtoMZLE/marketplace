package escrow

import (
	"context"
	"errors"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/marketplace/payment/internal/chain"
)

type Status string

const (
	StatusLocked   Status = "locked"
	StatusReleased Status = "released"
	StatusRefunded Status = "refunded"
	StatusDisputed Status = "disputed"
)

type Account struct {
	ID         string    `json:"id"`
	OrderID    string    `json:"order_id"`
	CustomerID string    `json:"customer_id"`
	ExecutorID string    `json:"executor_id"`
	Amount     float64   `json:"amount"`
	Status     Status    `json:"status"`
	CreatedAt  time.Time `json:"created_at"`
}

type Store struct {
	mu       sync.RWMutex
	accounts map[string]*Account
	balances map[string]float64
	chain    *chain.Chain
	pool     *pgxpool.Pool
}

// Global is the production singleton, initialised by main after DB setup.
var Global *Store

var (
	ErrNotFound          = errors.New("escrow account not found")
	ErrBadStatus         = errors.New("escrow account is not in expected status")
	ErrInsufficientFunds = errors.New("insufficient funds")
)

func NewStore(pool *pgxpool.Pool) *Store {
	s := &Store{
		accounts: make(map[string]*Account),
		balances: make(map[string]float64),
		chain:    &chain.Chain{},
		pool:     pool,
	}
	if pool != nil {
		s.loadFromDB()
	}
	return s
}

// ── Persistence helpers ───────────────────────────────────────────

func (s *Store) persistTx(tx *chain.Transaction) {
	if s.pool == nil {
		return
	}
	_, err := s.pool.Exec(context.Background(),
		`INSERT INTO blockchain (id, ts, from_id, to_id, amount, prev_hash, hash, description)
		 VALUES ($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT (id) DO NOTHING`,
		tx.ID, tx.Timestamp, tx.From, tx.To, tx.Amount, tx.PrevHash, tx.Hash, tx.Description)
	if err != nil {
		log.Printf("persist blockchain tx: %v", err)
	}
}

func (s *Store) persistAccount(acc *Account) {
	if s.pool == nil {
		return
	}
	_, err := s.pool.Exec(context.Background(),
		`INSERT INTO escrow_accounts (id, order_id, customer_id, executor_id, amount, status, created_at)
		 VALUES ($1,$2,$3,$4,$5,$6,$7)
		 ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status`,
		acc.ID, acc.OrderID, acc.CustomerID, acc.ExecutorID, acc.Amount, acc.Status, acc.CreatedAt)
	if err != nil {
		log.Printf("persist escrow account: %v", err)
	}
}

func (s *Store) persistBalance(userID string, balance float64) {
	if s.pool == nil {
		return
	}
	_, err := s.pool.Exec(context.Background(),
		`INSERT INTO escrow_balances (user_id, balance) VALUES ($1,$2)
		 ON CONFLICT (user_id) DO UPDATE SET balance = EXCLUDED.balance`,
		userID, balance)
	if err != nil {
		log.Printf("persist balance: %v", err)
	}
}

func (s *Store) loadFromDB() {
	ctx := context.Background()

	// Blockchain
	rows, err := s.pool.Query(ctx,
		`SELECT id, ts, from_id, to_id, amount, prev_hash, hash, description
		 FROM blockchain ORDER BY idx`)
	if err != nil {
		log.Printf("load blockchain: %v", err)
	} else {
		var txs []*chain.Transaction
		for rows.Next() {
			tx := &chain.Transaction{}
			var desc *string
			if err := rows.Scan(&tx.ID, &tx.Timestamp, &tx.From, &tx.To,
				&tx.Amount, &tx.PrevHash, &tx.Hash, &desc); err != nil {
				log.Printf("scan blockchain row: %v", err)
				continue
			}
			if desc != nil {
				tx.Description = *desc
			}
			txs = append(txs, tx)
		}
		rows.Close()
		s.chain.Load(txs)
		log.Printf("loaded %d blockchain transactions", len(txs))
	}

	// Escrow accounts
	rows2, err := s.pool.Query(ctx,
		`SELECT id, order_id, customer_id, executor_id, amount, status, created_at
		 FROM escrow_accounts`)
	if err != nil {
		log.Printf("load escrow accounts: %v", err)
	} else {
		for rows2.Next() {
			acc := &Account{}
			if err := rows2.Scan(&acc.ID, &acc.OrderID, &acc.CustomerID, &acc.ExecutorID,
				&acc.Amount, &acc.Status, &acc.CreatedAt); err != nil {
				log.Printf("scan escrow account: %v", err)
				continue
			}
			s.accounts[acc.ID] = acc
		}
		rows2.Close()
		log.Printf("loaded %d escrow accounts", len(s.accounts))
	}

	// Balances
	rows3, err := s.pool.Query(ctx, `SELECT user_id, balance FROM escrow_balances`)
	if err != nil {
		log.Printf("load balances: %v", err)
	} else {
		for rows3.Next() {
			var userID string
			var balance float64
			if err := rows3.Scan(&userID, &balance); err != nil {
				log.Printf("scan balance: %v", err)
				continue
			}
			s.balances[userID] = balance
		}
		rows3.Close()
		log.Printf("loaded %d balances", len(s.balances))
	}
}

// ── Store operations ──────────────────────────────────────────────

func (s *Store) Deposit(userID string, amount float64) {
	s.mu.Lock()
	s.balances[userID] += amount
	bal := s.balances[userID]
	s.mu.Unlock()

	s.persistBalance(userID, bal)
}

func (s *Store) Balance(userID string) float64 {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.balances[userID]
}

func (s *Store) Lock(orderID, customerID, executorID string, amount float64) (*Account, error) {
	s.mu.Lock()

	if s.balances[customerID] < amount {
		s.mu.Unlock()
		return nil, ErrInsufficientFunds
	}
	s.balances[customerID] -= amount
	balCopy := s.balances[customerID]

	acc := &Account{
		ID:         uuid.NewString(),
		OrderID:    orderID,
		CustomerID: customerID,
		ExecutorID: executorID,
		Amount:     amount,
		Status:     StatusLocked,
		CreatedAt:  time.Now().UTC(),
	}
	s.accounts[acc.ID] = acc
	tx := s.chain.Add(uuid.NewString(), customerID, fmt.Sprintf("escrow:%s", acc.ID), amount, "lock")

	s.mu.Unlock()

	s.persistAccount(acc)
	s.persistBalance(customerID, balCopy)
	s.persistTx(tx)
	return acc, nil
}

func (s *Store) Release(escrowID string) (*Account, error) {
	s.mu.Lock()

	acc, ok := s.accounts[escrowID]
	if !ok {
		s.mu.Unlock()
		return nil, ErrNotFound
	}
	if acc.Status != StatusLocked {
		s.mu.Unlock()
		return nil, ErrBadStatus
	}
	acc.Status = StatusReleased
	s.balances[acc.ExecutorID] += acc.Amount
	balCopy := s.balances[acc.ExecutorID]
	tx := s.chain.Add(uuid.NewString(), fmt.Sprintf("escrow:%s", acc.ID), acc.ExecutorID, acc.Amount, "release")

	s.mu.Unlock()

	s.persistAccount(acc)
	s.persistBalance(acc.ExecutorID, balCopy)
	s.persistTx(tx)
	return acc, nil
}

func (s *Store) Refund(escrowID string) (*Account, error) {
	s.mu.Lock()

	acc, ok := s.accounts[escrowID]
	if !ok {
		s.mu.Unlock()
		return nil, ErrNotFound
	}
	if acc.Status != StatusLocked {
		s.mu.Unlock()
		return nil, ErrBadStatus
	}
	acc.Status = StatusRefunded
	s.balances[acc.CustomerID] += acc.Amount
	balCopy := s.balances[acc.CustomerID]
	tx := s.chain.Add(uuid.NewString(), fmt.Sprintf("escrow:%s", acc.ID), acc.CustomerID, acc.Amount, "refund")

	s.mu.Unlock()

	s.persistAccount(acc)
	s.persistBalance(acc.CustomerID, balCopy)
	s.persistTx(tx)
	return acc, nil
}

func (s *Store) Dispute(escrowID string) (*Account, error) {
	s.mu.Lock()

	acc, ok := s.accounts[escrowID]
	if !ok {
		s.mu.Unlock()
		return nil, ErrNotFound
	}
	if acc.Status != StatusLocked {
		s.mu.Unlock()
		return nil, ErrBadStatus
	}
	acc.Status = StatusDisputed
	tx := s.chain.Add(uuid.NewString(), acc.CustomerID, acc.ExecutorID, acc.Amount, "dispute")

	s.mu.Unlock()

	s.persistAccount(acc)
	s.persistTx(tx)
	return acc, nil
}

func (s *Store) Get(escrowID string) (*Account, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	acc, ok := s.accounts[escrowID]
	if !ok {
		return nil, ErrNotFound
	}
	return acc, nil
}

func (s *Store) Chain() *chain.Chain {
	return s.chain
}

// TamperChain corrupts a transaction's amount in memory AND in the DB (demo only).
// The hash is intentionally NOT updated, so Verify() will detect the tampering.
func (s *Store) TamperChain(index int) (string, bool) {
	id, ok := s.chain.Tamper(index)
	if !ok || s.pool == nil {
		return id, ok
	}
	txs := s.chain.All()
	if index >= 0 && index < len(txs) {
		_, err := s.pool.Exec(context.Background(),
			`UPDATE blockchain SET amount = $1 WHERE id = $2`,
			txs[index].Amount, id)
		if err != nil {
			log.Printf("persist tamper: %v", err)
		}
	}
	return id, ok
}
