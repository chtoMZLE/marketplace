package handlers

import (
	"net/http"

	"github.com/marketplace/payment/internal/chain"
	"github.com/marketplace/payment/internal/escrow"
)

func RegisterChainRoutes(mux *http.ServeMux) {
	mux.HandleFunc("GET /chain", chainHandler)
	mux.HandleFunc("GET /chain/verify", chainVerifyHandler)
}

func chainHandler(w http.ResponseWriter, _ *http.Request) {
	txs := escrow.Global.Chain().All()
	if txs == nil {
		txs = []*chain.Transaction{}
	}
	respond(w, txs, http.StatusOK)
}

func chainVerifyHandler(w http.ResponseWriter, _ *http.Request) {
	broken := escrow.Global.Chain().Verify()
	if len(broken) == 0 {
		respond(w, map[string]any{"valid": true}, http.StatusOK)
		return
	}
	respond(w, map[string]any{"valid": false, "broken": broken}, http.StatusOK)
}
