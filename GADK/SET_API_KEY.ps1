# PowerShell script to set OpenAI API key
# Usage: .\SET_API_KEY.ps1
# Or run: $env:OPENAI_API_KEY="your-api-key-here"

Write-Host "Setting OpenAI API Key..." -ForegroundColor Green
Write-Host ""
Write-Host "Please enter your OpenAI API key:" -ForegroundColor Yellow
$apiKey = Read-Host -AsSecureString
$apiKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKey))
$env:OPENAI_API_KEY = $apiKeyPlain
Write-Host ""
Write-Host "API Key set successfully!" -ForegroundColor Green
Write-Host "You can now run: python app.py" -ForegroundColor Cyan

