package db

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"
)

const schema = `
CREATE TABLE IF NOT EXISTS blockchain (
    idx         SERIAL      PRIMARY KEY,
    id          TEXT        NOT NULL UNIQUE,
    ts          TIMESTAMPTZ NOT NULL,
    from_id     TEXT        NOT NULL,
    to_id       TEXT        NOT NULL,
    amount      FLOAT8      NOT NULL,
    prev_hash   TEXT        NOT NULL,
    hash        TEXT        NOT NULL,
    description TEXT
);
CREATE TABLE IF NOT EXISTS escrow_accounts (
    id          TEXT        PRIMARY KEY,
    order_id    TEXT        NOT NULL,
    customer_id TEXT        NOT NULL,
    executor_id TEXT        NOT NULL,
    amount      FLOAT8      NOT NULL,
    status      TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS escrow_balances (
    user_id TEXT   PRIMARY KEY,
    balance FLOAT8 NOT NULL DEFAULT 0
);
`

func Connect(ctx context.Context, dsn string) (*pgxpool.Pool, error) {
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, err
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, err
	}
	return pool, nil
}

func InitSchema(ctx context.Context, pool *pgxpool.Pool) error {
	_, err := pool.Exec(ctx, schema)
	return err
}
