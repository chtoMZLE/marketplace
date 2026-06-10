package chain

import (
	"crypto/sha256"
	"fmt"
	"sync"
	"time"
)

const genesisHash = "0000000000000000"

type Transaction struct {
	ID          string    `json:"id"`
	Timestamp   time.Time `json:"timestamp"`
	From        string    `json:"from"`
	To          string    `json:"to"`
	Amount      float64   `json:"amount"`
	PrevHash    string    `json:"prev_hash"`
	Hash        string    `json:"hash"`
	Description string    `json:"description,omitempty"`
}

// Load restores pre-computed transactions from persistent storage (no hash recalculation).
func (c *Chain) Load(txs []*Transaction) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.transactions = make([]*Transaction, len(txs))
	copy(c.transactions, txs)
}

// ComputeHash calculates SHA-256 over the deterministic fields of the transaction.
func ComputeHash(t *Transaction) string {
	raw := fmt.Sprintf("%s%s%s%s%.8f%s",
		t.ID,
		t.Timestamp.UTC().Format(time.RFC3339Nano),
		t.From,
		t.To,
		t.Amount,
		t.PrevHash,
	)
	sum := sha256.Sum256([]byte(raw))
	return fmt.Sprintf("%x", sum)
}

type Chain struct {
	mu           sync.RWMutex
	transactions []*Transaction
}

// Add appends a new transaction to the chain and sets its hash.
func (c *Chain) Add(id, from, to string, amount float64, desc string) *Transaction {
	c.mu.Lock()
	defer c.mu.Unlock()

	prev := genesisHash
	if len(c.transactions) > 0 {
		prev = c.transactions[len(c.transactions)-1].Hash
	}

	tx := &Transaction{
		ID:          id,
		Timestamp:   time.Now().UTC().Truncate(time.Microsecond),
		From:        from,
		To:          to,
		Amount:      amount,
		PrevHash:    prev,
		Description: desc,
	}
	tx.Hash = ComputeHash(tx)
	c.transactions = append(c.transactions, tx)
	return tx
}

// All returns a copy of the full chain.
func (c *Chain) All() []*Transaction {
	c.mu.RLock()
	defer c.mu.RUnlock()
	out := make([]*Transaction, len(c.transactions))
	copy(out, c.transactions)
	return out
}

// Tamper silently modifies a transaction's amount without recalculating hashes.
// Used only for demo purposes to show that Verify detects tampering.
func (c *Chain) Tamper(index int) (string, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if index < 0 || index >= len(c.transactions) {
		return "", false
	}
	c.transactions[index].Amount += 9999
	return c.transactions[index].ID, true
}

type BrokenRecord struct {
	Index int    `json:"index"`
	ID    string `json:"id"`
}

// Verify re-computes every hash and checks prev_hash linkage.
// Returns list of broken records (1-based index + ID), empty slice if chain is intact.
func (c *Chain) Verify() []BrokenRecord {
	c.mu.RLock()
	defer c.mu.RUnlock()

	var broken []BrokenRecord
	prev := genesisHash
	for i, tx := range c.transactions {
		if tx.PrevHash != prev || ComputeHash(tx) != tx.Hash {
			broken = append(broken, BrokenRecord{Index: i + 1, ID: tx.ID})
		}
		prev = tx.Hash
	}
	return broken
}
