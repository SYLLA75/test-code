CREATE TABLE IF NOT EXISTS clusters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  control_plane TEXT NOT NULL,
  workers TEXT NOT NULL,
  ssh_user TEXT NOT NULL,
  private_key_path TEXT NOT NULL,
  k8s_version TEXT DEFAULT '1.29.0',
  cni_plugin TEXT DEFAULT 'calico',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cluster_id INTEGER,
  run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  k8s_version TEXT,
  success INTEGER,
  log_path TEXT,
  FOREIGN KEY(cluster_id) REFERENCES clusters(id)
);
