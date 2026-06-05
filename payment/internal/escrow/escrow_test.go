package escrow_test

import (
	"errors"
	"testing"

	"github.com/marketplace/payment/internal/escrow"
)

func newStore(customerBalance float64) *escrow.Store {
	s := escrow.NewStore()
	if customerBalance > 0 {
		s.Deposit("customer1", customerBalance)
	}
	return s
}

func TestLock_Success(t *testing.T) {
	s := newStore(500)
	acc, err := s.Lock("order1", "customer1", "executor1", 100)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if acc.Status != escrow.StatusLocked {
		t.Fatalf("expected locked, got %s", acc.Status)
	}
	if s.Balance("customer1") != 400 {
		t.Fatalf("expected balance 400, got %f", s.Balance("customer1"))
	}
}

func TestLock_InsufficientFunds(t *testing.T) {
	s := newStore(50)
	_, err := s.Lock("order1", "customer1", "executor1", 100)
	if !errors.Is(err, escrow.ErrInsufficientFunds) {
		t.Fatalf("expected ErrInsufficientFunds, got %v", err)
	}
}

func TestRelease_Success(t *testing.T) {
	s := newStore(500)
	acc, _ := s.Lock("order1", "customer1", "executor1", 100)
	released, err := s.Release(acc.ID)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if released.Status != escrow.StatusReleased {
		t.Fatalf("expected released, got %s", released.Status)
	}
	if s.Balance("executor1") != 100 {
		t.Fatalf("expected executor balance 100, got %f", s.Balance("executor1"))
	}
}

func TestRefund_Success(t *testing.T) {
	s := newStore(500)
	acc, _ := s.Lock("order1", "customer1", "executor1", 100)
	refunded, err := s.Refund(acc.ID)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if refunded.Status != escrow.StatusRefunded {
		t.Fatalf("expected refunded, got %s", refunded.Status)
	}
	if s.Balance("customer1") != 500 {
		t.Fatalf("expected customer balance restored to 500, got %f", s.Balance("customer1"))
	}
}

func TestRelease_NotFound(t *testing.T) {
	s := newStore(0)
	_, err := s.Release("nonexistent")
	if !errors.Is(err, escrow.ErrNotFound) {
		t.Fatalf("expected ErrNotFound, got %v", err)
	}
}
