# Vacature scraper brokerplaformen
Deze tool scraped automatisch elke nacht vacatures van verschillende brokerplatformen, en matcht de best passende vacatures bij een CV dat je upload.
Link naar de tool: https://cv-v2-app-673359121713.europe-west4.run.app <br>
<br>
Het wordt gerund met Docker via Google Cloud Run Jobs: https://console.cloud.google.com/run/jobs/details/europe-west4/cv-scraper-job-v3/executions?authuser=0&hl=nl&inv=1&invt=Ab2eJA&project=potent-terminal-465211-d3
<br>
<br>
Nadat je code heb aangepast, navigeer binnen de Google Cloud Shell Terminal naar deze repo, pull de nieuwe code en run het volgende (zorg dat Docker runt): <br>
1. Image bouwen: <br>
   ```gcloud builds submit . --tag gcr.io/potent-terminal-465211-d3/cv-scraper-job-v3:latest``` <br>
2. Aanpassingen updaten: <br>
   ```gcloud run jobs update cv-scraper-job-v3 --image gcr.io/potent-terminal-465211-d3/cv-scraper-job-v3 --region europe-west4```<br>
3. Run de nieuwe job: <br>
   ```gcloud run jobs execute cv-scraper-job-v3 --region europe-west4```
