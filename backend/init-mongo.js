// MongoDB initialization script
db = db.getSiblingDB('spkia');

// Create collections
db.createCollection('jobs');
db.createCollection('proofs');
db.createCollection('metrics');

print('SPKIA database initialized successfully');
