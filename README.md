#  RentDao: Peer-to-Peer Rental Marketplace

RentDao is a full-stack, peer-to-peer rental marketplace built with FastAPI and MySQL. It empowers users to securely rent items to one another while integrating a fully automated, 3-tier logistics pipeline for delivery drivers and administrators.

##  Key Features

* **Three-Tier Architecture:** Dedicated portals and authorization logic for Standard Users, Delivery Drivers, and Administrators.
* **Secure Authentication:** Cookie-based session management and password hashing via `bcrypt` for secure, role-based access control.
* **Advanced Marketplace:** Users can perform full CRUD operations on items, including multi-image file uploads, custom dynamic pricing, and discounts.
* **Tag-Based Search Engine:** Custom search algorithm utilizing optimized raw SQL `LIKE` queries to match item tags, names, and descriptions, complete with state-preserving pagination.
* **Automated Logistics Pipeline:** An integrated Driver Dashboard where delivery personnel can view available jobs, accept deliveries, and automatically complete item bookings in real-time.
* **Admin Moderation Panel:** A robust control center for admins to approve/delete items, suspend/unsuspend users, and dismiss user reports.

## 🛠️ Tech Stack

* **Backend:** FastAPI (Python)
* **Database:** MySQL (hosted on TiDB Cloud)
* **ORM & Queries:** SQLAlchemy (used for database schema generation) alongside highly optimized raw SQL (`sqlalchemy.text`) for complex `JOIN` operations.
* **Frontend:** HTML, CSS, Jinja2 Templates
* **Security:** `bcrypt`, Python `secrets`, FastAPI Cookie/Session middleware

##  Project Structure

```text
RentDao/
├── main.py               # Application entry point and router registration
├── database.py           # TiDB Cloud MySQL connection setup
├── models.py             # SQLAlchemy schema definitions
├── security.py           # Password hashing and verification
├── routers/              # Modular backend logic
│   ├── auth.py           # User registration and login
│   ├── items.py          # Marketplace, tag search, and multi-image uploads
│   ├── booking.py        # Booking request and approval pipeline
│   ├── driver.py         # Delivery driver authentication and dashboard
│   └── admin.py          # Admin moderation and search panel
├── static/               
│   └── items/            # Directory for locally uploaded item images
└── templates/            # Jinja2 HTML templates
    ├── index.html        # Landing page
    ├── browse.html       # Marketplace and search engine
    ├── profile.html      # User dashboard and item management
    ├── admin.html        # Admin moderation panel
    └── driver_*.html     # Driver portals



