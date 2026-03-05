-- ============================================
-- SCHÉMA DE BASE DE DONNÉES - GESTION OUTILS IT
-- ============================================

-- Table principale : Outils/Équipements IT
CREATE TABLE IF NOT EXISTS tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    brand VARCHAR(50) NOT NULL,
    product_id VARCHAR(20),
    serial_number VARCHAR(9) UNIQUE NOT NULL,
    type VARCHAR(30) NOT NULL,
    localisation VARCHAR(100) DEFAULT 'Stock Principal',
    status VARCHAR(20) DEFAULT 'AVAILABLE' CHECK(status IN ('ACTIVE', 'MAINTENANCE', 'LENT OUT', 'AVAILABLE')),
    warranty_expiration DATE,
    battery_health INTEGER CHECK(battery_health >= 0 AND battery_health <= 100),
    assigned_to VARCHAR(100),
    purchase_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLE : RÔLES UTILISATEUR
-- ============================================
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(30) UNIQUE NOT NULL CHECK(name IN ('CEO', 'IT_MANAGER', 'IT_TECHNICIAN')),
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLE : UTILISATEURS
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password VARCHAR(64) NOT NULL,
    phone_number VARCHAR(20),
    date_of_birth DATE,
    address TEXT,
    gender VARCHAR(10),
    profile_photo TEXT,
    role_id INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT
);

-- ============================================
-- TABLE : CONSOMMABLES / FOURNITURES
-- ============================================
CREATE TABLE IF NOT EXISTS supplies (
    id TEXT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    section VARCHAR(50) NOT NULL,
    in_storage INTEGER DEFAULT 0,
    limit_alert INTEGER DEFAULT 5,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- ============================================
-- TABLE : ROOMS (Salles/Capacités pour la Map)
-- ============================================
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    icon VARCHAR(50) DEFAULT 'building',
    max_capacity INTEGER DEFAULT 10,
    room_type VARCHAR(50) DEFAULT 'office',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDEX POUR OPTIMISATION
-- ============================================
CREATE INDEX IF NOT EXISTS idx_tools_serial ON tools(serial_number);
CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status);
CREATE INDEX IF NOT EXISTS idx_tools_type ON tools(type);
CREATE INDEX IF NOT EXISTS idx_tools_assigned ON tools(assigned_to);
CREATE INDEX IF NOT EXISTS idx_supplies_search ON supplies(name, category, section);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- ============================================
-- TRIGGERS POUR MISE À JOUR AUTOMATIQUE
-- ============================================
CREATE TRIGGER IF NOT EXISTS update_tools_timestamp 
AFTER UPDATE ON tools
FOR EACH ROW
BEGIN
    UPDATE tools SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_users_timestamp
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_supplies_timestamp
AFTER UPDATE ON supplies
FOR EACH ROW
BEGIN
    UPDATE supplies SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_rooms_timestamp 
AFTER UPDATE ON rooms
FOR EACH ROW
BEGIN
    UPDATE rooms SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================
-- TABLE : NOTIFICATIONS (Historique des actions)
-- ============================================
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    related_id VARCHAR(50),
    actor_name VARCHAR(100),
    actor_role VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
