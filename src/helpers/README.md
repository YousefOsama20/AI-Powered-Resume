# Helpers Directory Overview

The `helpers` folder in this project serves as a central location for utility scripts and configuration management. Its primary role is to provide reusable helper functions and settings configurations, such as reading environment variables (via `.env`), which can be accessed consistently throughout the application (e.g., in controllers and routes).

## Files in `helpers/`

### 1. `config.py`

This file is responsible for loading and defining application-wide settings and configuration variables using Pydantic.

#### `Settings` (Class)
- **What it does:** Inherits from `pydantic_settings.BaseSettings`. It defines the schema and types for all the environment variables and configuration properties used across the app (such as application metadata, file upload constraints, vector DB paths, and embedding model settings). It is configured to automatically load these values from a `.env` file.
- **Role:** Main helper class (configuration schema).
- **Where it is used:** Used as a type hint and schema definition for configuration. It is imported and utilized in:
  - `src/controllers/BaseController.py`
  - `src/routes/base.py`
  - `src/routes/data.py`

#### `get_settings` (Function)
- **What it does:** Instantiates the `Settings` class and returns it. It is decorated with `functools.lru_cache()`, ensuring that the settings are only read from the `.env` file once and then cached for all subsequent calls, improving performance.
- **Role:** Main helper function.
- **Where it is used:** Used as the primary method to inject settings into routes and controllers. It is imported and utilized in:
  - `src/controllers/BaseController.py` (Called during `__init__` to set `self.app_settings`)
  - `src/routes/base.py` (Passed as a FastAPI `Depends` dependency in the endpoints)
  - `src/routes/data.py` (Passed as a FastAPI `Depends` dependency in the endpoints)
