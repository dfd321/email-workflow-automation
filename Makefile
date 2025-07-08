# Makefile for email_workflow_automation

.PHONY: all build up down logs

all: build up

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f
