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
Absolutely Bishal! ✨ Let’s upgrade the style, structure, and formatting to make your `README.md` look **attractive, modern, and super clean** — something that immediately catches attention when someone opens your project. Here's the enhanced and polished version with:

* Emojis 🪄
* Badges 📛
* Sections 🔥
* Clean hierarchy 💡
* Visual layout 📐

---

```markdown
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

## 📸 Demo

> 📍 *Insert screenshots or a screen recording here to visually demonstrate your app!*

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

## 📁 Folder Structure

```

Sales-and-Customer-Management/
├── core/                 # Business logic (models, views, etc.)
├── templates/            # HTML templates
├── static/               # CSS, JS, images
├── media/                # Uploaded files
├── notifications/        # Alerts and email logic
├── requirements.txt      # Dependencies
└── manage.py             # Django CLI entry point

````

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
````

### 2️⃣ Create & Activate Virtual Environment

```bash
python -m venv venv
```

* **Windows**:

  ```bash
  venv\Scripts\activate
  ```
* **Mac/Linux**:

  ```bash
  source venv/bin/activate
  ```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🧩 Database Setup

### Option A: SQLite (Default)

```bash
python manage.py migrate
```

### Option B: PostgreSQL

In `settings.py`, configure your DB connection:

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

Then login at ➡ [http://localhost:8000/admin](http://localhost:8000/admin)

---

## 🖨️ PDF Setup: wkhtmltopdf

This tool is used to generate PDFs (invoices/reports).

### 🔧 Install on Windows:

1. Download from [https://wkhtmltopdf.org/downloads.html](https://wkhtmltopdf.org/downloads.html)
2. Install and add this path to your **Environment Variables**:
   `C:\Program Files\wkhtmltopdf\bin`
3. Verify:

   ```bash
   wkhtmltopdf --version
   ```

---

## 📬 Email Notification Setup

In `settings.py`, configure:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@gmail.com'
EMAIL_HOST_PASSWORD = 'your_app_password'
```

💡 Use an [App Password](https://support.google.com/accounts/answer/185833?hl=en) if you use Gmail with 2FA.

---

## 🌟 Future Enhancements

* 📊 Dashboard with charts and analytics
* 🧑‍💼 Role-based access (Admin, Staff, etc.)
* 🎨 Custom invoice templates
* 📥 Excel exports
* 🌍 Multi-language support
* 🔐 API integration with DRF

---

## 🤝 Contributing

1. 🍴 Fork the project
2. 🌱 Create your branch (`git checkout -b feature`)
3. 💥 Make changes and commit (`git commit -am 'Add feature'`)
4. 🚀 Push to the branch (`git push origin feature`)
5. 📝 Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

Made with ❤️ by [**Bishal Somare**](https://github.com/Bishal-Somare)

---

```

---

### 🔥 Next Suggestions (Optional)

If you're posting this publicly:

- Add screenshots of the dashboard, admin panel, and email/PDF output.
- Create a `demo.mp4` or GIF showing login > low stock alert > generate PDF.
- Add deploy instructions for **Railway** (let me know, I’ll add it!).

Let me know if you want to add that or if you'd like a version in **dark mode (markdown style)** or a **PDF version of this README**!
```


