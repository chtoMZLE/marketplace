package escrow

import (
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/marketplace/payment/internal/chain"
)

type Status string

const (
	StatusLocked   Status = "locked"
	StatusReleased Status = "released"
	StatusRefunded Status = "refunded"
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
}

// Global is the production singleton.
var Global = NewStore()

var (
	ErrNotFound          = errors.New("escrow account not found")
	ErrBadStatus         = errors.New("escrow account is not in expected status")
	ErrInsufficientFunds = errors.New("insufficient funds")
)

// NewStore creates a new in-memory escrow store backed by its own chain.
func NewStore() *Store {
	return &Store{
		accounts: make(map[string]*Account),
		balances: make(map[string]float64),
		chain:    &chain.Chain{},
	}
}

func (s *Store) Deposit(userID string, amount float64) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.balances[userID] += amount
}

func (s *Store) Balance(userID string) float64 {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.balances[userID]
}

func (s *Store) Lock(orderID, customerID, executorID string, amount float64) (*Account, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.balances[customerID] < amount {
		return nil, ErrInsufficientFunds
	}
	s.balances[customerID] -= amount

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

	s.chain.Add(uuid.NewString(), customerID, fmt.Sprintf("escrow:%s", acc.ID), amount, "lock")
	return acc, nil
}

func (s *Store) Release(escrowID string) (*Account, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	acc, ok := s.accounts[escrowID]
	if !ok {
		return nil, ErrNotFound
	}
	if acc.Status != StatusLocked {
		return nil, ErrBadStatus
	}
	acc.Status = StatusReleased
	s.balances[acc.ExecutorID] += acc.Amount

	s.chain.Add(uuid.NewString(), fmt.Sprintf("escrow:%s", acc.ID), acc.ExecutorID, acc.Amount, "release")
	return acc, nil
}

func (s *Store) Refund(escrowID string) (*Account, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	acc, ok := s.accounts[escrowID]
	if !ok {
		return nil, ErrNotFound
	}
	if acc.Status != StatusLocked {
		return nil, ErrBadStatus
	}
	acc.Status = StatusRefunded
	s.balances[acc.CustomerID] += acc.Amount

	s.chain.Add(uuid.NewString(), fmt.Sprintf("escrow:%s", acc.ID), acc.CustomerID, acc.Amount, "refund")
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

// Chain returns the transaction chain (for the /chain endpoint).
func (s *Store) Chain() *chain.Chain {
	return s.chain
}
