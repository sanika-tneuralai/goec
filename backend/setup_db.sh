#!/bin/bash
# PostgreSQL Setup Script for GOEC Analytics

echo "Starting PostgreSQL setup..."

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL not found. Installing..."
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
fi

# Start PostgreSQL service
echo "Starting PostgreSQL service..."
sudo service postgresql start

# Check cluster status
sudo pg_lsclusters

# Set postgres user password
echo "Setting postgres user password..."
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';" 2>/dev/null

# Create database if not exists
echo "Creating goec database..."
sudo -u postgres psql -c "CREATE DATABASE goec;" 2>/dev/null || echo "Database already exists"

# Verify connection
echo "Testing connection..."
PGPASSWORD=postgres psql -h localhost -U postgres -d goec -c "SELECT version();" | head -3

echo ""
echo "PostgreSQL setup complete!"
echo "Database: goec"
echo "User: postgres"
echo "Password: postgres"
echo "Port: 5432"
echo ""
echo "Connection string: postgresql://postgres:postgres@localhost:5432/goec"
