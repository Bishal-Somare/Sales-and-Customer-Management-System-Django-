<h1 align="center">🛍️ Sales and Customer Management System</h1>

<p align="center">
  A powerful web app built with <strong>Django 5.2</strong> for managing customers, sales, inventory, and vendors.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Django-5.2-green?style=for-the-badge&logo=django" />
  <img src="https://img.shields.io/badge/PostgreSQL-Supported-blue?style=for-the-badge&logo=postgresql" />
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" />
</p>

---

---

## 🚀 Features

✅ Customer management with **pending payment email** alerts  
📦 Product & inventory management with **low-stock notifications**  
🤝 Vendor management  
🔐 Secure login/logout system  
📄 PDF generation using `wkhtmltopdf`  
📬 Email notifications for customers  
🌐 Responsive & dynamic UI using **HTML, CSS, JavaScript, AJAX**  
🧠 Follows Django’s **MVT (Model-View-Template)** architecture  
🗄️ Uses **PostgreSQL** (or SQLite for local testing)

---

---

## ⚙️ Tech Stack

| Layer      | Technology                      |
|------------|----------------------------------|
| Backend    | Django 5.2 (Python)              |
| Frontend   | HTML, CSS, JavaScript, AJAX     |
| Database   | PostgreSQL (or SQLite optional) |
| Extras     | `wkhtmltopdf` for PDF support   |

---

## ✅ Prerequisites

Make sure the following tools are installed:

- ✅ Python 3.9+
- ✅ PostgreSQL (or SQLite)
- ✅ pip
- ✅ Git
- ✅ `wkhtmltopdf` ➡ [Download](https://wkhtmltopdf.org/downloads.html)

---

## 🛠️ Local Setup Guide

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Bishal-Somare/Sales-and-Customer-Management-System-Django-.git
cd Sales-and-Customer-Management-System-Django-

### 2️⃣ Create & Activate Virtual Environment

```bash
python -m venv venv
```

**Windows:**

```bash
venv\Scripts\activate
```

**Mac/Linux:**

```bash
source venv/bin/activate
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🧩 Database Setup

### 🔹 Option A: SQLite (Default)

```bash
python manage.py migrate
```

---

### 🔹 Option B: PostgreSQL

In `settings.py`, configure your database:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Then run:

```bash
python manage.py migrate
```

---

## 👤 Create Superuser

```bash
python manage.py createsuperuser
```

Then login at:
👉 [http://localhost:8000/admin](http://localhost:8000/admin)

---

## 🖨️ PDF Setup: `wkhtmltopdf`

This tool is used to generate PDF reports and invoices.

### 🔧 Install on Windows:

1. Download from: [https://wkhtmltopdf.org/downloads.html](https://wkhtmltopdf.org/downloads.html)
2. Install and add this path to your **Environment Variables**:

   ```
   C:\Program Files\wkhtmltopdf\bin
   ```
3. Verify installation:

```bash
wkhtmltopdf --version
```

---

## 📬 Email Notification Setup

Open `settings.py` and add your email configuration:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@gmail.com'
EMAIL_HOST_PASSWORD = 'your_app_password'
```

> 💡 Use a [Gmail App Password](https://support.google.com/accounts/answer/185833?hl=en) if you have 2FA enabled.

---

## 🌟 Future Enhancements

* 🔐 REST API integration with Django REST Framework

---

## 🤝 Contributing

```bash
🍴 Fork the project
🌱 Create your branch (git checkout -b feature)
💥 Make changes and commit (git commit -am 'Add feature')
🚀 Push to the branch (git push origin feature)
📝 Open a Pull Request
```


