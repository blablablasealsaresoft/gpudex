#!/bin/bash

# GPUDex Database Backup Script
# Creates automated backups of PostgreSQL database

set -e

# Configuration
DB_HOST="postgres"
DB_NAME="gpudex"
DB_USER="gpudex"
BACKUP_DIR="/backups"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="gpudex_backup_${DATE}.sql"
RETENTION_DAYS=30

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

echo "🔄 Starting GPUDex database backup at $(date)"

# Create database backup
echo "📦 Creating database dump..."
pg_dump -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} --no-password > ${BACKUP_DIR}/${BACKUP_FILE}

# Compress the backup
echo "🗜️ Compressing backup..."
gzip ${BACKUP_DIR}/${BACKUP_FILE}

# Create a symlink to the latest backup
ln -sf ${BACKUP_FILE}.gz ${BACKUP_DIR}/latest_backup.sql.gz

echo "✅ Backup completed: ${BACKUP_FILE}.gz"

# Cleanup old backups (keep only last 30 days)
echo "🧹 Cleaning up old backups..."
find ${BACKUP_DIR} -name "gpudx_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# Calculate backup size
BACKUP_SIZE=$(du -h ${BACKUP_DIR}/${BACKUP_FILE}.gz | cut -f1)
echo "📊 Backup size: ${BACKUP_SIZE}"

# List current backups
echo "📁 Current backups:"
ls -lah ${BACKUP_DIR}/gpudx_backup_*.sql.gz | tail -5

echo "🎉 Backup process completed successfully at $(date)" 