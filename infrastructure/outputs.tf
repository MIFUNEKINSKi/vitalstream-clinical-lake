output "landing_zone_bucket" {
  value = aws_s3_bucket.landing_zone.bucket
}

output "curated_zone_bucket" {
  value = aws_s3_bucket.curated_zone.bucket
}

output "glue_database_name" {
    value = aws_glue_catalog_database.vitalstream_db.name
}

output "glue_crawler_name" {
    value = aws_glue_crawler.vitalstream_crawler.name
}
