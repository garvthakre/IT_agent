from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import random
import string
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nexus-it-agent-secret"

DB_PATH = "database.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_temp_password():
    chars = string.ascii_uppercase + string.digits
    return "TMP-" + "".join(random.choices(chars, k=8))


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    active = db.execute("SELECT COUNT(*) FROM users WHERE status='active'").fetchone()[0]
    disabled = db.execute("SELECT COUNT(*) FROM users WHERE status='disabled'").fetchone()[0]
    recent = db.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 5").fetchall()
    db.close()
    return render_template("dashboard.html", total=total, active=active, disabled=disabled, recent=recent)


@app.route("/users")
def users():
    db = get_db()
    search = request.args.get("search", "").strip()
    if search:
        all_users = db.execute(
            "SELECT * FROM users WHERE name LIKE ? OR email LIKE ? ORDER BY name",
            (f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        all_users = db.execute("SELECT * FROM users ORDER BY name").fetchall()
    db.close()
    return render_template("users.html", users=all_users, search=search)


@app.route("/create-user", methods=["GET", "POST"])
def create_user():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "employee")

        if not name or not email:
            flash("Name and email are required.", "error")
            return render_template("create_user.html")

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            flash(f"User with email {email} already exists.", "error")
            db.close()
            return render_template("create_user.html")

        temp_pass = generate_temp_password()
        db.execute(
            "INSERT INTO users (name, email, role, status, password, created_at) VALUES (?,?,?,?,?,?)",
            (name, email, role, "active", temp_pass, datetime.now().isoformat())
        )
        db.commit()
        db.close()
        flash(f"User {name} ({email}) created successfully. Temporary password: {temp_pass}", "success")
        return redirect(url_for("users"))

    return render_template("create_user.html")


@app.route("/reset-password/<int:user_id>", methods=["GET", "POST"])
def reset_password(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    if not user:
        flash("User not found.", "error")
        db.close()
        return redirect(url_for("users"))

    if request.method == "POST":
        new_pass = generate_temp_password()
        db.execute("UPDATE users SET password=? WHERE id=?", (new_pass, user_id))
        db.commit()
        db.close()
        return render_template("confirm.html",
            action="Password Reset",
            user=user,
            message=f"Password for {user['email']} has been reset successfully.",
            detail=f"New temporary password: {new_pass}",
            new_password=new_pass
        )

    db.close()
    return render_template("reset_confirm.html", user=user)


@app.route("/toggle-status/<int:user_id>", methods=["POST"])
def toggle_status(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    if not user:
        flash("User not found.", "error")
        db.close()
        return redirect(url_for("users"))

    new_status = "disabled" if user["status"] == "active" else "active"
    action_word = "disabled" if new_status == "disabled" else "enabled"

    db.execute("UPDATE users SET status=? WHERE id=?", (new_status, user_id))
    db.commit()
    db.close()

    return render_template("confirm.html",
        action="Account Status Changed",
        user=user,
        message=f"Account for {user['email']} has been {action_word}.",
        detail=f"Current status: {new_status.upper()}",
        new_password=None
    )


@app.route("/delete-user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    if not user:
        flash("User not found.", "error")
        db.close()
        return redirect(url_for("users"))

    name = user["name"]
    email = user["email"]
    db.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    db.close()

    return render_template("confirm.html",
        action="User Deleted",
        user=user,
        message=f"User {name} ({email}) has been permanently deleted.",
        detail="This action cannot be undone.",
        new_password=None
    )


@app.route("/user/<int:user_id>")
def user_detail(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    db.close()
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("users"))
    return render_template("user_detail.html", user=user)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
