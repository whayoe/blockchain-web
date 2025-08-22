# blockchain.py
import hashlib
import json
import time
import os
import sqlite3

def init_db():
    conn = sqlite3.connect('blockchain.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS blocks (
            index_block INTEGER,
            transactions TEXT,
            timestamp REAL,
            previous_hash TEXT,
            hash TEXT,
            nonce INTEGER,
            difficulty INTEGER
        )
    ''')
    conn.commit()
    conn.close()
    
# Fungsi hash
def hash_function(data):
    return hashlib.sha256(data.encode()).hexdigest()

# Kelas Block
class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, difficulty=3):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.difficulty = difficulty
        self.nonce = 0
        self.hash = self.mine_block()

    def compute_hash(self):
        block_string = f"{self.index}{self.transactions}{self.timestamp}{self.previous_hash}{self.nonce}"
        return hash_function(block_string)

    def mine_block(self):
        target = '0' * self.difficulty
        while self.compute_hash()[:self.difficulty] != target:
            self.nonce += 1
        return self.compute_hash()

    def to_dict(self):
        return {
            'index': self.index,
            'transactions': self.transactions,
            'timestamp': self.timestamp,  # Simpan sebagai float
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'nonce': self.nonce,
            'difficulty': self.difficulty
        }


# Kelas Blockchain
class Blockchain:
    def __init__(self, data_file="blockchain_data.json", difficulty=3):
        self.data_file = data_file
        self.difficulty = difficulty
        self.chain = []
        self.load_chain()
        if len(self.chain) == 0:
            self.create_genesis_block()

    def create_genesis_block(self):
        genesis = Block(0, "Genesis Block", time.time(), "0", self.difficulty)
        self.chain.append(genesis)
        self.save_chain()

    def add_block(self, transactions):
        last_block = self.chain[-1]
        new_block = Block(
            index=last_block.index + 1,
            transactions=transactions,
            timestamp=time.time(),
            previous_hash=last_block.hash,
            difficulty=self.difficulty
        )
        self.chain.append(new_block)
        self.save_chain()

    def save_chain(self):
        data = []
        for block in self.chain:
            block_data = block.to_dict()
            block_data['timestamp'] = block.timestamp  # Pastikan float
            data.append(block_data)
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"✅ Data disimpan ke {self.data_file}")

    def load_chain(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                for item in data:
                    block = Block(
                        index=int(item['index']),
                        transactions=item['transactions'],
                        timestamp=float(item['timestamp']),
                        previous_hash=item['previous_hash'],
                        difficulty=int(item['difficulty'])
                    )
                    block.nonce = int(item['nonce'])
                    block.hash = item['hash']
                    self.chain.append(block)
                print(f"✅ Data dimuat dari {self.data_file}")
            except Exception as e:
                print(f"❌ Gagal memuat file: {e}")
        else:
            print("📁 File data belum ada. Akan dibuat saat blok pertama ditambahkan.")

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.hash != current.compute_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
        return True

    def get_chain(self):
        result = []
        for block in self.chain:
            block_dict = block.to_dict()
            block_dict['timestamp'] = time.ctime(block_dict['timestamp'])
            result.append(block_dict)
        return result

    def calculate_balances(self):
        """Hitung saldo semua pengguna berdasarkan transaksi"""
        balances = {}
        for block in self.chain:
            tx = block.transactions
            if " -> " in tx and ": Rp" in tx:
                try:
                    sender_part = tx.split(" -> ")[0]
                    rest = tx.split(" -> ")[1]
                    receiver = rest.split(":")[0].strip()
                    amount_str = rest.split(":")[1].strip()
                    if amount_str.startswith("Rp"):
                        amount = int(amount_str[2:])
                    else:
                        amount = int(amount_str)
                    balances[sender_part] = balances.get(sender_part, 0) - amount
                    balances[receiver] = balances.get(receiver, 0) + amount
                except Exception as e:
                    print(f"Error parsing transaction '{tx}': {e}")
        return balances