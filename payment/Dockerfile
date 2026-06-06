FROM golang:1.23-alpine AS builder

WORKDIR /app

COPY . .
RUN go mod tidy && go build -o server ./cmd/server

FROM alpine:3.20 AS runner

WORKDIR /app

COPY --from=builder /app/server .

EXPOSE 8001

CMD ["./server"]
