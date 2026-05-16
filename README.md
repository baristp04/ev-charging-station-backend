# EV Charging Station Network Management System - Backend

This repository contains the backend application and API for the Electric Vehicle (EV) Charging Station Network Management System, developed as part of the **Fundamentals of Software Engineering** course.

## 📖 About the Project

This project serves as the core backend infrastructure for the EV Charging Station platform. It manages business logic, database schemas, and RESTful APIs required to support the frontend application. The backend handles critical operations including user wallet transactions, charging station status updates, reservation scheduling, and the enforcement of system policies.

## ✨ Features

* **RESTful API Architecture:** Provides robust endpoints for frontend integration and client communication.
* **Vehicle Management:** Allows users to register and manage their electric vehicles to streamline the charging and reservation process.
* **Station Reservation Logic:** Handles the backend processing for booking, validating, and managing charging slot reservations.
* **Station Maintenance Mode:** Administrative features to set stations to maintenance mode, preventing new reservations and charging sessions while offline.
* **Wallet & Transaction Engine:** Securely manages user balances, top-ups, and exact deductions based on charging session data.
* **Session Control Processing:** Processes start/stop commands for charging sessions and tracks session durations.
* **Policy Enforcement:** Strict implementation of business rules, including the policy of no refunds for early termination of charging sessions.
* **Database Management:** Well-structured backend schemas for managing users, vehicles, stations, reservations, and financial transactions.

## 🛠 Tech Stack

* **Backend Framework:** FastAPI (Python)
* **Database:** PostgreSQL / SQLite (Update based on your configuration)
* **ORM:** SQLModel 
* **Authentication:** JWT (JSON Web Tokens)
* **ASGI Server:** Uvicorn

## 🎓 Academic Context

This project was developed for the **Fundamentals of Software Engineering** course in the Computer Engineering curriculum at **Ege University**.
