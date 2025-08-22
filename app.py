from flask import Flask, render_template, request, redirect, url_for, session
import bcrypt
from blockchain import Blockchain
import secrets  # Untuk buat token acak

# Inisialisasi Flask dan Blockchain
app = Flask(__name__)
app.secret_key = 'rahasia123'

# Inisialisasi blockchain
bc = Blockchain()

# === 🔐 DI SINI: DEFINISIKAN USERS_HASHED ===
USERS_HASHED = {
    'admin': b'$2b$12$KxhS9y6Gq3e2Z7v8W9x0Y.3a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u',
    'andi':  b'$2b$12$AxByCz1234567890abcdef.g1h2i3j4k5l6m7n8o9p0q1r2s3t4u5v6w7x8y9z0'
}
# ==========================================

# === 🔐 FUNGSI HASH & CEK PASSWORD ===
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)
# =====================================
# Simpan token sementara (di production, gunakan database)
RESET_TOKENS = {}

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        
        if username in USERS_HASHED:
            # Buat token acak
            token = secrets.token_urlsafe(32)
            RESET_TOKENS[token] = username  # Simpan: token → username
            reset_link = url_for('reset_password', token=token, _external=True)
            
            # Tampilkan link (di dunia nyata, kirim via email)
            return f"""
            <h3>🔐 Link Reset Password</h3>
            <p>Salin link di bawah ini (hanya berlaku sekali):</p>
            <p><a href="{reset_link}">{reset_link}</a></p>
            <p><a href="/login">« Kembali ke login</a></p>
            """
        else:
            return render_template('forgot_password.html', error="Username tidak ditemukan!")
    
    return render_template('forgot_password.html')
    
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if token not in RESET_TOKENS:
        return "❌ Link tidak valid atau sudah digunakan.", 400

    username = RESET_TOKENS[token]

    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('password_confirm')

        if new_password != confirm_password:
            return render_template('reset_password.html', error="Password tidak cocok!", username=username)

        if len(new_password) < 6:
            return render_template('reset_password.html', error="Password minimal 6 karakter!", username=username)

        # Hash password baru
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        USERS_HASHED[username] = hashed
        del RESET_TOKENS[token]  # Hapus token setelah dipakai

        return render_template('reset_success.html', username=username)

    return render_template('reset_password.html', username=username)

# === RUTE: Halaman Utama (Publik) ===
@app.route('/')
def index():
    chain = bc.get_chain()
    valid = bc.is_chain_valid()
    logged_in = 'username' in session
    return render_template('index.html', chain=chain, valid=valid, logged_in=logged_in, bc=bc)

# === RUTE: Login ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Cek apakah username ada
        if username in USERS_HASHED:
            # Cek password dengan bcrypt
            if check_password(password, USERS_HASHED[username]):
                session['username'] = username
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="Password salah!")
        else:
            return render_template('login.html', error="Username tidak ditemukan!")
    
    return render_template('login.html')

# === RUTE: Logout ===
@app.route('/logout')
def logout():
    session.pop('username', None)  # Hapus username dari session
    return redirect(url_for('index'))

# === RUTE: Tambah Transaksi (Hanya untuk yang login) ===
@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if 'username' not in session:
        return redirect(url_for('login'))

    error = None
    success = None

    if request.method == 'POST':
        tx = request.form.get('transaction')

        # ✅ Validasi format
        if not tx:
            error = "Transaksi tidak boleh kosong!"
        elif " -> " not in tx:
            error = 'Format salah! Harus: "A -> B: Rp10000"'
        elif ": Rp" not in tx:
            error = 'Format salah! Jumlah harus diawali "Rp"'
        else:
            # Ambil bagian jumlah
            try:
                amount_part = tx.split(":")[1].strip()
                if not amount_part.startswith("Rp"):
                    error = 'Jumlah harus diawali "Rp"'
                else:
                    amount_str = amount_part[2:]  # Hilangkan "Rp"
                    if not amount_str.isdigit():
                        error = "Jumlah harus angka (contoh: Rp10000)"
                    else:
                        amount = int(amount_str)
                        if amount <= 0:
                            error = "Jumlah harus lebih dari 0"
            except:
                error = "Gagal membaca jumlah uang"

        # 🔐 Validasi Saldo (Opsional: Cegah Saldo Negatif)
        if not error:
            balances = bc.calculate_balances()
            sender = tx.split(" -> ")[0]
            current_balance = balances.get(sender, 0)
            amount = int(tx.split(":")[1].strip()[2:])

            if current_balance < amount:
                error = f"Saldo tidak cukup! {sender} hanya punya Rp{current_balance:,}"

        # 🔽 Jika tidak ada error, tambahkan transaksi
        if not error:
            full_tx = f"[{session['username']}] {tx}"
            print(f"Menambang blok baru: {full_tx}")
            bc.add_block(full_tx)
            success = f"Transaksi '{tx}' berhasil ditambahkan!"
            tx = ""  # Kosongkan form

    return render_template('add.html', error=error, success=success)

@app.route('/topup', methods=['GET', 'POST'])
def topup():
    if 'username' not in session:
        return redirect(url_for('login'))

    error = None
    success = None

    if request.method == 'POST':
        amount_str = request.form.get('amount')
        try:
            amount = int(amount_str)
            if amount <= 0:
                error = "Jumlah harus lebih dari 0"
            else:
                # Buat transaksi "Top Up": dari sistem ke user
                tx = f"[{session['username']}] Sistem -> {session['username']}: Rp{amount}"
                print(f"Menambang top up: {tx}")
                bc.add_block(tx)
                success = f"✅ Saldo berhasil ditambahkan sebesar Rp{amount:,}!"
        except ValueError:
            error = "Jumlah harus angka"

    return render_template('topup.html', error=error, success=success)

# Jalankan server
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)