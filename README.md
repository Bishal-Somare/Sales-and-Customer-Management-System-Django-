# Sales and Customer Management System

## 🔧 Prerequisites

This project requires [`wkhtmltopdf`](https://wkhtmltopdf.org/downloads.html) to generate PDF reports.

### 🛠️ Install wkhtmltopdf on Windows

1. Download the Windows installer from the official site:  
   👉 [https://wkhtmltopdf.org/downloads.html](https://wkhtmltopdf.org/downloads.html)

2. Install it by running the downloaded `.exe` file.

3. After installation, add the path to the `bin` directory to your system's **Environment Variables**:
   - Typically the path looks like:  
     `C:\Program Files\wkhtmltopdf\bin`
   - To add it to your environment variables:
     - Press `Windows + S` and search for **Environment Variables**.
     - Click **Edit the system environment variables**.
     - In the **System Properties** window, click **Environment Variables**.
     - Under **System Variables**, select the `Path` variable and click **Edit**.
     - Click **New**, then paste the path (e.g., `C:\Program Files\wkhtmltopdf\bin`).
     - Click **OK** on all dialogs.

4. To verify the installation:
   - Open Command Prompt and type:
     ```sh
     wkhtmltopdf --version
     ```
   - You should see the installed version.

---

Now you can run PDF generation features in the project without issues.


