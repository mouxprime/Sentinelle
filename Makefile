.PHONY: help build up down start stop restart logs clean ps status shell-frontend shell-db health rebuild dev prod

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Affiche cette aide
	@echo "$(BLUE)Global Threat Map - Docker Management$(NC)"
	@echo ""
	@echo "$(GREEN)Commandes disponibles:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'

build: ## Construit les images Docker
	@echo "$(BLUE)Construction des images Docker...$(NC)"
	docker-compose build

up: ## Démarre tous les services en arrière-plan
	@echo "$(BLUE)Démarrage des services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services démarrés! Application disponible sur http://localhost$(NC)"

down: ## Arrête et supprime tous les conteneurs
	@echo "$(BLUE)Arrêt des services...$(NC)"
	docker-compose down

start: up ## Alias pour 'up'

stop: down ## Alias pour 'down'

restart: ## Redémarre tous les services
	@echo "$(BLUE)Redémarrage des services...$(NC)"
	docker-compose restart

logs: ## Affiche les logs de tous les services
	docker-compose logs -f

logs-frontend: ## Affiche les logs du frontend uniquement
	docker-compose logs -f frontend

logs-nginx: ## Affiche les logs de nginx uniquement
	docker-compose logs -f nginx

logs-db: ## Affiche les logs de la base de données uniquement
	docker-compose logs -f database

clean: ## Arrête les services et supprime volumes et images
	@echo "$(YELLOW)Nettoyage complet...$(NC)"
	docker-compose down -v --rmi all
	@echo "$(GREEN)Nettoyage terminé!$(NC)"

ps: ## Liste les conteneurs en cours d'exécution
	docker-compose ps

status: ## Affiche le statut des services
	@echo "$(BLUE)Statut des services:$(NC)"
	@docker-compose ps

shell-frontend: ## Ouvre un shell dans le conteneur frontend
	docker-compose exec frontend sh

shell-db: ## Ouvre un shell PostgreSQL
	docker-compose exec database psql -U globalthreat -d globalthreatmap

shell-db-bash: ## Ouvre un shell bash dans le conteneur database
	docker-compose exec database sh

health: ## Vérifie la santé de tous les services
	@echo "$(BLUE)Vérification de la santé des services...$(NC)"
	@docker-compose ps
	@echo ""
	@echo "$(BLUE)Nginx Health Check:$(NC)"
	@curl -s http://localhost/health || echo "$(YELLOW)Nginx non disponible$(NC)"

rebuild: ## Reconstruit et redémarre tous les services
	@echo "$(BLUE)Reconstruction et redémarrage...$(NC)"
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "$(GREEN)Services reconstruits et redémarrés!$(NC)"

dev: ## Lance le projet en mode développement (avec docker-compose)
	@echo "$(BLUE)Démarrage en mode développement...$(NC)"
	docker-compose up --build

prod: build up ## Build et lance en production (détaché)

init: ## Initialise le projet (copie .env.example vers .env si nécessaire)
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Création du fichier .env depuis .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN).env créé! Pensez à configurer vos variables d'environnement.$(NC)"; \
	else \
		echo "$(GREEN)Le fichier .env existe déjà.$(NC)"; \
	fi

backup-db: ## Sauvegarde la base de données
	@echo "$(BLUE)Sauvegarde de la base de données...$(NC)"
	@mkdir -p backups
	docker-compose exec -T database pg_dump -U globalthreat globalthreatmap > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Sauvegarde créée dans le dossier backups/$(NC)"

restore-db: ## Restaure la base de données (usage: make restore-db FILE=backups/backup.sql)
	@if [ -z "$(FILE)" ]; then \
		echo "$(YELLOW)Usage: make restore-db FILE=backups/backup.sql$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Restauration de la base de données depuis $(FILE)...$(NC)"
	docker-compose exec -T database psql -U globalthreat globalthreatmap < $(FILE)
	@echo "$(GREEN)Base de données restaurée!$(NC)"

# Par défaut, affiche l'aide
.DEFAULT_GOAL := help
