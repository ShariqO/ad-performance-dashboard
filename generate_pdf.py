import os

pdf_content = r"""%PDF-1.4
1 0 obj
<<
  /Type /Catalog
  /Pages 2 0 R
>>
endobj
2 0 obj
<<
  /Type /Pages
  /Kids [3 0 R]
  /Count 1
>>
endobj
3 0 obj
<<
  /Type /Page
  /Parent 2 0 R
  /Resources <<
    /Font <<
      /F1 4 0 R
    >>
  >>
  /MediaBox [0 0 612 792]
  /Contents 5 0 R
>>
endobj
4 0 obj
<<
  /Type /Font
  /Subtype /Type1
  /BaseFont /Helvetica
>>
endobj
5 0 obj
<<
  /Length 520
>>
stream
BT
/F1 18 Tf
50 730 Td
(Google Ads API Tool Documentation) Tj
/F1 12 Tf
0 -30 Td
(Application Name: Ad Performance Dashboard) Tj
0 -20 Td
(Author / Developer: Independent Developer) Tj
0 -30 Td
(1. Overview & Purpose:) Tj
0 -15 Td
(The Ad Performance Dashboard is a read-only analytics data pipeline.) Tj
0 -15 Td
(It extracts performance metrics (impressions, clicks, spend, conversions)) Tj
0 -15 Td
(from Google Ads API using GAQL queries.) Tj
0 -30 Td
(2. Architecture & Data Flow:) Tj
0 -15 Td
(1) Authenticate via OAuth2 + Developer Token) Tj
0 -15 Td
(2) Query campaign performance via GoogleAdsService.SearchStream) Tj
0 -15 Td
(3) Normalize metrics into a standard schema) Tj
0 -15 Td
(4) Load partitioned records into Google BigQuery) Tj
0 -15 Td
(5) Display visual reports on a private Streamlit dashboard) Tj
0 -30 Td
(3. Scope of API Access:) Tj
0 -15 Td
(Read-only reporting. No campaign mutation, account creation, or automated bidding.) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000313 00000 n 
trailer
<<
  /Size 6
  /Root 1 0 R
>>
startxref
884
%%EOF
"""

with open("Google_Ads_API_Tool_Documentation.pdf", "wb") as f:
    f.write(pdf_content.encode("latin1"))

print("PDF created successfully!")
