# 📚 Standar Penamaan ERD & DDL Database (Enterprise Convention)

Dokumen ini menjadi standar pembuatan **ERD, DDL, dan desain database** untuk seluruh aplikasi agar konsisten, mudah dipahami, scalable, dan mempermudah proses maintenance.

---

# 1. Penamaan Tabel

Gunakan prefix berdasarkan jenis data.

| Jenis Data                   | Prefix | Contoh                |
| ---------------------------- | ------ | --------------------- |
| Data Master (jarang berubah) | `mst_` | `mst_category`        |
| Data Transaksi               | `trx_` | `trx_order`           |
| Data History                 | `his_` | `his_order_status`    |
| Data Log                     | `log_` | `log_activity`        |
| Data Mapping                 | `map_` | `map_role_permission` |
| Data Konfigurasi             | `cfg_` | `cfg_setting`         |
| Data Temporary               | `tmp_` | `tmp_import_product`  |

---

# 2. Penamaan Tabel Menggunakan Singular

Gunakan bentuk tunggal (singular).

✅ Benar

```text
mst_category
mst_customer
trx_order
trx_product
```

❌ Salah

```text
mst_categories
mst_customers
trx_orders
trx_products
```

---

# 3. Primary Key

Primary key menggunakan singkatan nama tabel.

Format:

```text
<prefix_singkat>_id
```

Contoh:

| Nama Tabel       | Primary Key |
| ---------------- | ----------- |
| mst_category     | mc_id       |
| mst_supplier     | ms_id       |
| trx_product      | tp_id       |
| trx_order        | to_id       |
| trx_order_detail | tod_id      |

---

# 4. Foreign Key

Foreign key mengikuti format:

```text
<prefix_tabel_sendiri>_<primary_key_tabel_referensi>
```

Contoh:

Tabel:

```text
mst_category
mc_id
```

Direferensikan oleh:

```text
trx_product
```

menjadi:

```text
tp_mc_id
```

Bukan:

```text
category_id ❌

mc_id ❌
```

Tetapi:

```text
tp_mc_id ✅
```

Contoh lain:

```text
mst_supplier
ms_id

trx_product
```

menjadi:

```text
tp_ms_id
```

---

# 5. Penamaan Kolom

Semua kolom bisnis wajib menggunakan prefix tabel.

Contoh:

## mst_category

```text
mc_name
mc_description
mc_status
```

## trx_product

```text
tp_name
tp_price
tp_stock
tp_barcode
tp_weight
tp_status
```

Hal ini bertujuan agar saat melakukan JOIN antar banyak tabel, asal kolom tetap jelas tanpa perlu alias tambahan.

---

# 6. Audit Column

Kolom audit **tidak menggunakan prefix tabel** karena bersifat universal.

Standar nama:

```text
created_at
created_by

updated_at
updated_by

is_deleted

deleted_at
deleted_by
```

Contoh yang salah:

```text
tp_created_at ❌

mc_updated_at ❌
```

Contoh yang benar:

```text
created_at ✅

updated_at ✅

is_deleted ✅
```

---

# 7. Aturan Penggunaan Audit Column

Audit column digunakan sesuai karakteristik data pada tabel.

## A. Tabel Master Statis (Jarang atau Hampir Tidak Pernah Diubah)

Contoh:

```text
mst_gender
mst_religion
mst_country
mst_province
mst_city
mst_payment_method
```

Kolom yang digunakan:

```text
created_at
created_by
```

Tidak perlu:

```text
updated_at
updated_by
```

karena data bersifat referensi dan hampir tidak pernah mengalami perubahan setelah dibuat.

---

## B. Tabel Master Dinamis

Contoh:

```text
mst_product_category
mst_supplier
mst_customer
mst_employee
mst_user
mst_role
```

Kolom yang digunakan:

```text
created_at
created_by

updated_at
updated_by
```

karena data dapat diperbarui sewaktu-waktu.

---

## C. Tabel Transaksi

Contoh:

```text
trx_order
trx_product
trx_purchase
trx_invoice
trx_payment
```

Wajib memiliki:

```text
created_at
created_by

updated_at
updated_by
```

karena data transaksi dapat berubah status, nominal, atau informasi lainnya selama proses bisnis berlangsung.

---

## D. Soft Delete

Jika aplikasi menggunakan soft delete, tambahkan:

```text
is_deleted
deleted_at
deleted_by
```

Jika aplikasi menggunakan hard delete (data dihapus permanen), maka ketiga kolom tersebut tidak perlu dibuat.

---

# 8. Aturan Soft Delete

Gunakan:

```text
is_deleted BOOLEAN

deleted_at TIMESTAMP NULL

deleted_by VARCHAR(...)
```

Jangan langsung menghapus data transaksi penting agar histori tetap dapat ditelusuri.

---

# 9. Boolean

Selalu diawali dengan:

```text
is_
```

Contoh:

```text
is_active

is_deleted

is_verified

is_default

is_publish
```

---

# 10. Timestamp

Minimal:

```text
created_at
```

Jika data dapat diubah:

```text
updated_at
```

Jika menggunakan soft delete:

```text
deleted_at
```

---

# 11. User Audit

Gunakan:

```text
created_by

updated_by

deleted_by
```

untuk menyimpan identitas pengguna atau sistem yang melakukan perubahan.

---

# 12. Penamaan Constraint

Primary Key

```text
pk_trx_product

pk_mst_category
```

Foreign Key

```text
fk_trx_product_category

fk_trx_order_customer
```

Unique

```text
uq_category_name
```

Index

```text
idx_tp_barcode

idx_tp_name
```

---

# 13. Penamaan Index

Gunakan format:

```text
idx_<nama_kolom>
```

Contoh:

```text
idx_tp_barcode

idx_tp_name

idx_tp_status

idx_mc_name
```

---

# 14. Relasi Antar Tabel

Contoh:

```text
mst_category
--------------------
mc_id
mc_name

        ▲
        │
        │ tp_mc_id

trx_product
--------------------
tp_id
tp_mc_id
tp_name
tp_price
```

Foreign key selalu mengacu pada primary key tabel referensi.

---

# 15. Tabel Detail

Contoh:

```text
trx_order

to_id
```

detail:

```text
trx_order_detail

tod_id
tod_to_id
tod_tp_id
tod_qty
tod_price
```

Semua kolom mengikuti prefix tabel detail.

---

# 16. Standar DDL Audit Berdasarkan Jenis Tabel

| Jenis Tabel    | created_at | created_by | updated_at | updated_by |    is_deleted    |    deleted_at    |    deleted_by    |
| -------------- | :--------: | :--------: | :--------: | :--------: | :--------------: | :--------------: | :--------------: |
| Master statis  |      ✅     |      ✅     |      ❌     |      ❌     |     Opsional     |     Opsional     |     Opsional     |
| Master dinamis |      ✅     |      ✅     |      ✅     |      ✅     |     Opsional     |     Opsional     |     Opsional     |
| Transaksi      |      ✅     |      ✅     |      ✅     |      ✅     | Sesuai kebutuhan | Sesuai kebutuhan | Sesuai kebutuhan |
| History        |      ✅     |      ✅     |      ❌     |      ❌     |         ❌        |         ❌        |         ❌        |
| Log            |      ✅     |      ✅     |      ❌     |      ❌     |         ❌        |         ❌        |         ❌        |
| Mapping        |      ✅     |      ✅     |  Opsional  |  Opsional  |     Opsional     |     Opsional     |     Opsional     |
| Configuration  |      ✅     |      ✅     |      ✅     |      ✅     |     Opsional     |     Opsional     |     Opsional     |

---

# 17. Prinsip Utama

1. Gunakan **prefix tabel** untuk seluruh kolom bisnis.
2. **Primary key** menggunakan singkatan nama tabel (`mc_id`, `tp_id`, `to_id`).
3. **Foreign key** menggunakan format `<prefix_tabel_sendiri>_<primary_key_tabel_referensi>` (`tp_mc_id`, `tod_to_id`).
4. **Audit column tidak menggunakan prefix** (`created_at`, `updated_at`, `deleted_at`, dan sejenisnya).
5. Gunakan **`updated_at` dan `updated_by` hanya pada tabel yang memang memungkinkan perubahan data**. Untuk master yang benar-benar statis, kedua kolom tersebut tidak perlu ditambahkan.
6. Gunakan **`is_deleted`, `deleted_at`, dan `deleted_by` hanya jika menerapkan soft delete**.
7. Gunakan **snake_case**, nama tabel **singular**, dan penamaan yang konsisten di seluruh database.
8. Hindari nama kolom generik seperti `name`, `status`, atau `description`; gunakan nama yang telah diprefix sesuai tabel (`tp_name`, `mc_status`, `ms_description`) agar jelas saat digunakan dalam query kompleks.
