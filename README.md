
```markdown
# 🛍️ Sales and Customer Management System

A full-featured Django 5.2-based web application for managing products, vendors, inventory, customers, and sales with automated notifications, PDF generation, and a dynamic frontend.

🔗 **GitHub Repository**: [Sales and Customer Management System](https://github.com/Bishal-Somare/Sales-and-Customer-Management-System-Django-.git)

---

## 🚀 Features

- ✅ Customer management with pending payment email notifications  
- 📦 Inventory & product management with low stock alerts  
- 🤝 Vendor management  
- 🔐 Secure login/logout system  
- 📄 PDF generation of invoices & reports  
- 📬 Email alert system (pending payments)  
- 🔔 System notifications for low stock items  
- 🌐 Dynamic UI with HTML, CSS, JavaScript, and AJAX  
- 🧠 Follows Django’s MVT (Model-View-Template) architecture  
- 💾 Uses PostgreSQL (or SQLite for development/testing)  

---

## 📁 Project Structure

```

sales\_customer\_management/
│
├── core/                  # Main application logic
├── templates/             # HTML templates
├── static/                # CSS, JS, images
├── media/                 # Uploaded files
├── notifications/         # Email, alert systems
├── requirements.txt       # All dependencies
└── manage.py              # Django CLI

````

---

## ⚙️ Tech Stack

- Backend: Django 5.2  
- Frontend: HTML, CSS, JS, AJAX  
- Database: PostgreSQL (SQLite for dev/testing)  
- External Tools: `wkhtmltopdf` for PDF generation  

---

## ✅ Prerequisites

- Python 3.9+  
- PostgreSQL or SQLite  
- pip (Python package manager)  
- Git  
- `wkhtmltopdf` for PDF functionality  

---

## 🛠️ Installation & Setup

Follow these steps to set up the project on your local machine:

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Bishal-Somare/Sales-and-Customer-Management-System-Django-.git
cd Sales-and-Customer-Management-System-Django-
````

### 2️⃣ Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

* **Windows:**

  ```bash
  venv\Scripts\activate
  ```

* **macOS/Linux:**

  ```bash
  source venv/bin/activate
  ```

### 3️⃣ Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4️⃣ Set Up the Database

#### Option A: Use SQLite (default)

No setup needed. Just run:

```bash
python manage.py migrate
```

#### Option B: Use PostgreSQL

Update your `DATABASES` setting in `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Then apply migrations:

```bash
python manage.py migrate
```

---

### 5️⃣ Create Superuser

```bash
python manage.py createsuperuser
```

---

### 6️⃣ Run the Server

```bash
python manage.py runserver
```

Visit: [http://localhost:8000](http://localhost:8000)

---

## 🖨️ PDF Generation Setup

This project uses `wkhtmltopdf` to generate PDF reports/invoices.

### 📥 Install `wkhtmltopdf` on Windows

1. Download installer:
   👉 [https://wkhtmltopdf.org/downloads.html](https://wkhtmltopdf.org/downloads.html)

2. Run the `.exe` file to install.

3. Add the following path to **Environment Variables** (Path):

   ```
   C:\Program Files\wkhtmltopdf\bin
   ```

4. Verify installation:

```bash
wkhtmltopdf --version
```

---

## 📬 Email Setup for Notifications

Update `settings.py` with your email configuration:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@gmail.com'
EMAIL_HOST_PASSWORD = 'your_app_password'
```

> ⚠️ Use App Passwords if you have 2FA enabled on Gmail.

---

## 🔐 Admin Login

After creating a superuser, go to:

👉 [http://localhost:8000/admin](http://localhost:8000/admin)

---

## 🔮 Future Enhancements

* Dashboard analytics (charts)
* Role-based access control
* Invoice template customization
* Export reports to Excel
* API endpoints using DRF (optional)

---

## 🤝 Contributing

Want to improve this project? Fork the repo and make a pull request!
For suggestions or feature requests, open an issue.

---

## 📜 License

This project is licensed under the MIT License.

---

### ✨ Created by [Bishal Somare](https://github.com/Bishal-Somare)

```

---

Let me know if you’d like to include **screenshots**, **demo video**, or **deployment instructions** as well. I can help you polish this even further before sharing it publicly or in your portfolio!
```
