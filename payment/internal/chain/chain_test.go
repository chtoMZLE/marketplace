package chain_test

import (
	"testing"

	"github.com/marketplace/payment/internal/chain"
)

func TestComputeHash_Deterministic(t *testing.T) {
	c := &chain.Chain{}
	tx := c.Add("id1", "alice", "bob", 100.0, "test")
	// Re-compute and compare
	want := chain.ComputeHash(tx)
	if tx.Hash != want {
		t.Fatalf("hash mismatch: got %s want %s", tx.Hash, want)
	}
}

func TestChain_Verify_Valid(t *testing.T) {
	c := &chain.Chain{}
	c.Add("id1", "alice", "bob", 50.0, "lock")
	c.Add("id2", "escrow", "bob", 50.0, "release")

	broken := c.Verify()
	if len(broken) != 0 {
		t.Fatalf("expected valid chain, got broken: %v", broken)
	}
}

func TestChain_Verify_Tampered(t *testing.T) {
	c := &chain.Chain{}
	c.Add("id1", "alice", "bob", 50.0, "lock")
	tx2 := c.Add("id2", "escrow", "bob", 50.0, "release")

	// Tamper with tx2's hash
	tx2.Hash = "deadbeef"

	broken := c.Verify()
	if len(broken) == 0 {
		t.Fatal("expected broken chain but got valid")
	}
}

func TestChain_PrevHash_Genesis(t *testing.T) {
	c := &chain.Chain{}
	tx := c.Add("id1", "alice", "bob", 10.0, "lock")
	if tx.PrevHash != "0000000000000000" {
		t.Fatalf("first tx prevhash should be genesis, got %s", tx.PrevHash)
	}
}

func TestChain_PrevHash_Linking(t *testing.T) {
	c := &chain.Chain{}
	tx1 := c.Add("id1", "alice", "bob", 10.0, "lock")
	tx2 := c.Add("id2", "escrow", "bob", 10.0, "release")
	if tx2.PrevHash != tx1.Hash {
		t.Fatalf("tx2.prev_hash should equal tx1.hash")
	}
}
