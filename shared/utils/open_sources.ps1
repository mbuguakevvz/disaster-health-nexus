# ============================================================
# Disaster Health Nexus - Data Source Explorer
# Opens each real data source URL one by one in your browser
# ============================================================

$sources = @(
    @{
        Name        = "1. HDX - Humanitarian Data Exchange (Register for API Key)"
        Disease     = "BOTH"
        URL         = "https://data.humdata.org/user/register"
        Description = "Main data source. Register here and get your API key from your profile."
    },
    @{
        Name        = "2. HDX - Cholera Datasets"
        Disease     = "CHOLERA"
        URL         = "https://data.humdata.org/search?q=cholera"
        Description = "Browse all real cholera datasets available for download."
    },
    @{
        Name        = "3. HDX - Ebola Datasets"
        Disease     = "EBOLA"
        URL         = "https://data.humdata.org/search?q=ebola"
        Description = "Browse all real ebola datasets available for download."
    },
    @{
        Name        = "4. HDX - Health Facilities Africa"
        Disease     = "BOTH"
        URL         = "https://data.humdata.org/search?q=health+facilities+africa"
        Description = "Health facility locations across Africa."
    },
    @{
        Name        = "5. WHO - Global Health Observatory API"
        Disease     = "BOTH"
        URL         = "https://www.who.int/data/gho/info/gho-odata-api"
        Description = "WHO real-time disease data API documentation."
    },
    @{
        Name        = "6. WHO - Cholera Global Situation"
        Disease     = "CHOLERA"
        URL         = "https://www.who.int/news-room/fact-sheets/detail/cholera"
        Description = "WHO official cholera outbreak situation reports."
    },
    @{
        Name        = "7. WHO - Ebola Global Situation"
        Disease     = "EBOLA"
        URL         = "https://www.who.int/news-room/fact-sheets/detail/ebola-virus-disease"
        Description = "WHO official Ebola outbreak situation reports."
    },
    @{
        Name        = "8. ReliefWeb API - Cholera Outbreak Reports"
        Disease     = "CHOLERA"
        URL         = "https://api.reliefweb.int/v1/reports?appname=disaster-health-nexus"
        Description = "Live ReliefWeb API - cholera situation reports in raw JSON."
    },
    @{
        Name        = "9. UNHCR - Displaced Population Datasets"
        Disease     = "BOTH"
        URL         = "https://data.unhcr.org/en/documents/search?type=dataset"
        Description = "UNHCR refugee and IDP population datasets by country."
    },
    @{
        Name        = "10. UNHCR - Population Explorer"
        Disease     = "BOTH"
        URL         = "https://data.unhcr.org/population/"
        Description = "Interactive UNHCR population data explorer."
    },
    @{
        Name        = "11. OpenStreetMap Overpass - Health Facilities"
        Disease     = "BOTH"
        URL         = "https://overpass-turbo.eu/"
        Description = "Live OSM query tool - hospitals and clinics in Africa."
    },
    @{
        Name        = "12. Our World in Data - Cholera Deaths"
        Disease     = "CHOLERA"
        URL         = "https://ourworldindata.org/cholera"
        Description = "Historical and recent cholera case and death data, downloadable as CSV."
    },
    @{
        Name        = "13. Our World in Data - Ebola"
        Disease     = "EBOLA"
        URL         = "https://ourworldindata.org/ebola"
        Description = "Historical Ebola outbreak data, downloadable as CSV."
    },
    @{
        Name        = "14. Africa CDC - Disease Surveillance"
        Disease     = "BOTH"
        URL         = "https://africacdc.org/disease-surveillance/"
        Description = "Africa CDC real-time disease outbreak updates."
    },
    @{
        Name        = "15. Global Health - Cholera Open Dataset"
        Disease     = "CHOLERA"
        URL         = "https://global.health/topics/cholera/"
        Description = "Global.health open dataset - structured cholera case records."
    }
)

# ============================================================
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   DISASTER HEALTH NEXUS - Data Source Explorer"        -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Press ENTER to open each source, Q to quit."
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

foreach ($source in $sources) {

    $color = switch ($source.Disease) {
        "CHOLERA" { "Blue" }
        "EBOLA"   { "Red" }
        "BOTH"    { "Green" }
    }

    Write-Host "--------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "  $($source.Name)"        -ForegroundColor $color
    Write-Host "  Disease : $($source.Disease)"  -ForegroundColor $color
    Write-Host "  URL     : $($source.URL)"       -ForegroundColor Yellow
    Write-Host "  Info    : $($source.Description)" -ForegroundColor White
    Write-Host "--------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host ""

    $key = Read-Host "  Press ENTER to open | Type Q to quit"

    if ($key -eq "Q" -or $key -eq "q") {
        Write-Host ""
        Write-Host "  Exiting. Good luck!" -ForegroundColor Cyan
        break
    }

    Start-Process $source.URL
    Write-Host "  Opened in browser!" -ForegroundColor Green
    Write-Host ""
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  All sources reviewed."
Write-Host "  Next: Add your HDX API Key to your .env file"
Write-Host "  then run: python -m cholera.ingestion.hdx_cholera"
Write-Host "========================================================" -ForegroundColor Cyan