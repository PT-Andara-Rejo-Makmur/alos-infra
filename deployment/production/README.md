# Deployment Production

Production hanya dijalankan melalui approved change window oleh operator berwenang. Gunakan
immutable image, environment dari secret interface, verified backup, migration plan, rollback
reference, dan health verification. Bootstrap CI tidak memiliki deployment credential dan tidak
menjalankan production deployment.
