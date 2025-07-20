# BizDirectory

A modern Django application that connects users with local businesses in their area.

## Overview

BizDirectory helps users discover and connect with local businesses through an intuitive search interface. Business owners can create profiles, showcase services, and build their online presence with verification badges and customer reviews.

## Features

- **For Users**
  - Search businesses by category, location, or keywords
  - Filter by rating, trust badges (GST/KYC verification), and services
  - View business details including hours, services, and contact information
  - Submit reviews and request special offers/coupons
  - Contact businesses directly through the platform

- **For Business Owners**
  - Create and manage business profiles
  - Upload multiple images and showcase services
  - Respond to customer reviews and inquiries
  - Track business analytics through dashboard
  - Verification system for enhanced credibility (GST & KYC)

## Tech Stack

- **Backend**: Django 5.2
- **Frontend**: Bootstrap 5, jQuery, AJAX
- **Database**: SQLite (Development), PostgreSQL (Production)
- **Asynchronous Tasks**: Celery with Redis
- **Deployment**: Appliku with DigitalOcean

## Quick Start

### Clone repository
```bash
git clone https://github.com/rakeshptajlapur/bizdirectory.git
cd bizdirectory
```

### Setup virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install and run
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```


Visit http://127.0.0.1:8000/ to access the application.

### Status
This project is under active development. Features are being added regularly.

### Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

## Install dependencies
pip install -r requirements.txt

### Setup environment variables
Create a .env file in the project root with the following variables:
DJANGO_SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

### Run migrations and start server
python manage.py migrate
python manage.py collectstatic
python manage.py runserver 8080

Visit http://127.0.0.1:8080/ to access the application.

### Production Deployment
For production deployment, additional environment variables are required:

### Database configuration
Redis configuration for Celery
Email settings
Production domain names
See .env.example for a complete list of required variables.

### Project Structure
accounts - User authentication and profiles
directory - Core business listing functionality
media - User-uploaded content
config - Project settings and configuration

## Status
This project is under active development. Features are being added regularly.

## License
Copyright © 2025 FindNearBiz. All rights reserved.