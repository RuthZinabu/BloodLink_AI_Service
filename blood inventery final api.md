# BLOOD INVENTORY API DOCUMENTATION

Base URL:
```
/api/inventory
```

All endpoints require authentication via JWT.
---

# 1. GET ALL BLOOD UNITS

### `GET /api/inventory`

###  Access Roles:

*  BLOOD_BANK_ADMIN
* LAB_TECH

### Description:

Fetch all blood units with filtering and aggregation summary.

### Query Parameters:

| Param          | Type    | Description                          |
| -------------- | ------- | ------------------------------------ |
| blood_type     | string  | Filter by blood group (A+, O-, etc.) |
| component_type | string  | PLASMA, RBC, PLATELET, etc.          |
| status         | string  | AVAILABLE, RESERVED, USED, EXPIRED   |
| volume         | int     | Minimum volume (ml)                  |
| start_date     | string  | Collection start date                |
| end_date       | string  | Collection end date                  |
| near_expired   | boolean | true = expires within 7 days         |

### Response:

```json
{
  "total": 120,
  "available": 80,
  "reserved": 20,
  "used": 10,
  "expired": 5,
  "near_expired": 5,
  "by_blood_type": {
    "A+": 30,
    "O-": 25
  },
  "by_component_type": {
    "PLASMA": 40
  },
  "units": [
    {
      "blood_unit_id": "BU123",
      "blood_type": "A+",
      "component_type": "PLASMA",
      "volume_ml": 450,
      "status": "AVAILABLE",
      "collection_date": "2026-05-10",
      "expiration_date": "2026-06-10",
      "storage_location": "Freezer A",
      "rack_number": "R1",
      "shelf_number": "S2"
    }
  ]
}
```

---

# 2. GET BLOOD UNIT BY ID

### `GET /api/inventory/:id`

### Access Roles:

* BLOOD_BANK_ADMIN
* LAB_TECH

### Description:

Fetch basic details of a single blood unit.

---

# 3. GET INVENTORY STATISTICS

### `GET /api/inventory/stats`

### Access Roles:

* BLOOD_BANK_ADMIN
* LAB_TECH

### Description:

Returns aggregated inventory counts.

### Response:

```json
{
  "total": 200,
  "available": 120,
  "reserved": 30,
  "used": 20,
  "expired": 10,
  "nearExpiry": 15
}
```

---

# 4. EXPORT INVENTORY (CSV)

### `GET /api/inventory/export/csv`

Access Roles:

*BLOOD_BANK_ADMIN
LAB_TECH

### Description:

Download full inventory as CSV file.

---

# 5. EXPORT INVENTORY (PDF)

### `GET /api/inventory/export/pdf`

###  Access Roles:

*BLOOD_BANK_ADMIN
* LAB_TECH


### Description:

Download formatted PDF report of inventory.

---

#  6. GET FULL BLOOD UNIT DETAILS

### `GET /api/inventory/:id/details`

### 👤 Access Roles:

*  BLOOD_BANK_ADMIN
* LAB_TECH

### Description:

Returns enriched data including donor and test results.

---

# 7. DELETE BLOOD UNIT (SOFT DELETE + AUDIT)

### `DELETE /api/inventory/:id`
Access Roles:

*  BLOOD_BANK_ADMIN
* LAB_TECH


### Rules:

* Only allowed if status is:

  * `EXPIRED`
  * `USED`
* Creates audit log before deletion.

---

---

# 8. ### 4.2 Convert Plasma to Cryoprecipitate (Lab Only)
Allows a Lab Technician to convert an existing Plasma unit into Cryoprecipitate and Cryo-poor Plasma. The original Plasma unit is marked as soft-deleted.

**Endpoint:** `POST /api/inventory/:id/convert-cryo`

**Request Body:**
```json
{
  "cryoprecipitate_quantity": 15,
  "cryo_poor_plasma_quantity": 185
}
```
*(Note: `cryo_poor_plasma_quantity` is optional. If omitted, the system calculates it as a perfect split: Original Plasma Quantity - Cryoprecipitate Quantity. If the lab tech specifies a quantity, it handles standard processing/tubing losses)
**Response (200 OK):**
```json
{
  "message": "Plasma converted to Cryoprecipitate successfully"
}
```
* Status values:

  ```
  AVAILABLE | RESERVED | USED | EXPIRED
  ```

* Component types:

  ```
  PLASMA | RBC | PLATELET | WHOLE_BLOOD | CRYOPRECIPITATE | CRYO_POOR_PLASMA
  ```

* Near-expiry = automatically calculated within **7 days**

