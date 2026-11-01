# Jasiri Air - Flight Ticketing System

## Project Overview
This is an enterprise-grade Flight Ticketing System developed for **Jasiri Air** (formerly SkyLink). Built strictly with Python Flask, Jinja2, HTML5, CSS3, and SQLite, the application enables customers to search for flights, book tickets, manage reservations, and generate printable E-Tickets. The system features a secure role-based administrative portal for comprehensive CRUD operations on flight inventory and booking ledgers.

## Technical Architecture
* **Backend:** Python 3.8+, Flask 3.0
* **Templating:** Jinja2
* **Frontend:** HTML5, CSS3 (Custom Styling & Bootstrap 5)
* **Database:** SQLite (`flight_ticketing.db`) with SQLAlchemy ORM
* **Security:** Werkzeug password hashing, native Flask session management

## Setup and Installation

1. **Navigate to the project directory:**
   ```bash
   cd flight_ticketing_system

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt

## Database Initialization

- The application automatically generates the flight_ticketing.db database, creating all 5 required tables (flights, passengers, bookings, administrators, contact_messages) and seeding initial inventory upon startup.

## Running the Application

1. **Start the Flask development server:**
   ```bash
   python3 app.py

2. **Access Local Address:**
   Access the application at: 
   http://127.0.0.1:5000

## Administrative Credentials

1. **Access the Flight Management Dashboard**
   Access the Flight Management Dashboard at:
   http://127.0.0.1:5000/admin/login

   Use the following fictional credentials:
   - Username: admin
   - Password: admin123