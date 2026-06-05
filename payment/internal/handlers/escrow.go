package handlers

import (
	"encoding/json"
	"errors"
	"net/http"
	"strings"

	"github.com/marketplace/payment/internal/escrow"
)

type lockRequest struct {
	OrderID    string  `json:"order_id"`
	Amount     float64 `json:"amount"`
	CustomerID string  `json:"customer_id"`
	ExecutorID string  `json:"executor_id"`
}

type escrowIDRequest struct {
	EscrowID string `json:"escrow_id"`
}

func RegisterEscrowRoutes(mux *http.ServeMux) {
	mux.HandleFunc("POST /escrow/lock", lockHandler)
	mux.HandleFunc("POST /escrow/release", releaseHandler)
	mux.HandleFunc("POST /escrow/refund", refundHandler)
	mux.HandleFunc("GET /escrow/{id}", getEscrowHandler)
}

func lockHandler(w http.ResponseWriter, r *http.Request) {
	var req lockRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		httpError(w, "invalid request body", http.StatusBadRequest)
		return
	}
	if req.OrderID == "" || req.CustomerID == "" || req.ExecutorID == "" || req.Amount <= 0 {
		httpError(w, "order_id, customer_id, executor_id and positive amount are required", http.StatusBadRequest)
		return
	}

	acc, err := escrow.Global.Lock(req.OrderID, req.CustomerID, req.ExecutorID, req.Amount)
	if err != nil {
		if errors.Is(err, escrow.ErrInsufficientFunds) {
			httpError(w, "insufficient funds", http.StatusPaymentRequired)
			return
		}
		httpError(w, err.Error(), http.StatusInternalServerError)
		return
	}
	respond(w, acc, http.StatusCreated)
}

func releaseHandler(w http.ResponseWriter, r *http.Request) {
	var req escrowIDRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.EscrowID == "" {
		httpError(w, "escrow_id is required", http.StatusBadRequest)
		return
	}
	acc, err := escrow.Global.Release(req.EscrowID)
	if err != nil {
		handleEscrowErr(w, err)
		return
	}
	respond(w, acc, http.StatusOK)
}

func refundHandler(w http.ResponseWriter, r *http.Request) {
	var req escrowIDRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.EscrowID == "" {
		httpError(w, "escrow_id is required", http.StatusBadRequest)
		return
	}
	acc, err := escrow.Global.Refund(req.EscrowID)
	if err != nil {
		handleEscrowErr(w, err)
		return
	}
	respond(w, acc, http.StatusOK)
}

func getEscrowHandler(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(r.URL.Path, "/escrow/")
	acc, err := escrow.Global.Get(id)
	if err != nil {
		handleEscrowErr(w, err)
		return
	}
	respond(w, acc, http.StatusOK)
}

func handleEscrowErr(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, escrow.ErrNotFound):
		httpError(w, "escrow account not found", http.StatusNotFound)
	case errors.Is(err, escrow.ErrBadStatus):
		httpError(w, "escrow account is not in locked status", http.StatusConflict)
	default:
		httpError(w, err.Error(), http.StatusInternalServerError)
	}
}
