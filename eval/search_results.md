# Semantic search results

Run on 2026-11-14 with `sentence-transformers/all-MiniLM-L6-v2`. 62 chunks from 8 source pages (about 120 words per chunk, 25 words overlap). Every chunk keeps its source, page and title.

Each question is turned into an embedding and compared with every chunk by cosine similarity. The top 3 hits are listed. A best score below 0.3 is marked "no confident match".

## Summary
| # | Question | Best hit | Score | Result |
|---|---|---|---|---|
| 1 | I am OBC with Rs 3.2 lakh income. Which scholarship fits me? | Scholarship Scheme for Minority Students of the State pursuing Higher... | 0.64 | found |
| 2 | What is the difference between EBC and OBC Freeship? | Dr. Punjabrao Deshmukh Hostel Subsistence Allowance Scheme | 0.34 | found |
| 3 | Which documents do I need for MahaDBT? | Scholarship Scheme for Minority Students of the State pursuing Higher... | 0.54 | found |
| 4 | Is there an AICTE or NSP scholarship I can apply for? | AICTE - Saksham Scholarship Scheme For Specially Abled Student... | 0.64 | found |
| 5 | What is the last date to apply this year? | PM-USP – Central Sector Scheme Of Scholarship For College And... | 0.41 | found |
| 6 | What is the hostel fee at Sanjivani College of Engineering? | Scholarship For Top Class Education for Students with Disabilities | 0.53 | found |
| 7 | I am a girl studying engineering. Which schemes cover my tuition fee? | Scholarships for Higher Education Abroad to meritorious boys and... | 0.61 | found |
| 8 | My family income is Rs 6 lakh and I am from an EWS family. Can I get the Rajarshi... | Rajarshi Chhatrapati Shahu Maharaj Education Fee Scholarship Scheme | 0.78 | found |
| 9 | How much hostel allowance can I get if my parents are small-land farmers? | Dr. Punjabrao Deshmukh Hostel Subsistence Allowance Scheme | 0.46 | found |
| 10 | I belong to a minority community and my family income is Rs 2 lakh. Which scholarship can... | Scholarship Scheme for Minority Students of the State pursuing Higher... | 0.72 | found |

Every question had a confident match.

## Hits per question

### Q1. I am OBC with Rs 3.2 lakh income. Which scholarship fits me?

| Rank | Score | Title | Source | Page | Chunk starts with |
|---|---|---|---|---|---|
| 1 | 0.64 | Scholarship Scheme for Minority Students of the State pursuing Higher... | https://dte.maharashtra.gov.in/scholarship-for-students-of-minority-communities-pursuing-higher-and-professional-courses | 1 | From the academic year 2022-23, the following scholarship amount is provided to the eligible minority students who have come for new scholarship and... |
| 2 | 0.63 | Scholarship For Top Class Education for Students with Disabilities | https://dte.maharashtra.gov.in/scholarship-for-top-class-education-for-students-with-disabilities | 1 | सदर योजना केंद्र शासनाच्या National Scholarship Portal ( NSP ) पोर्टलद्वारे ( संकेतस्थळ – www.scholarships.gov.in ) ऑनलाईनरित्या राबविण्यात येते. सदर... |
| 3 | 0.63 | Scholarship For Top Class Education for Students with Disabilities | https://dte.maharashtra.gov.in/scholarship-for-top-class-education-for-students-with-disabilities | 1 | Desk 17 – QUALITY CELL Desk 18 – Scholarship Section Regional offices Amravati Chhatrapati Sambhaji Nagar Mumbai Nagpur Nashik Pune Citizen Charter... |

### Q2. What is the difference between EBC and OBC Freeship?

| Rank | Score | Title | Source | Page | Chunk starts with |
|---|---|---|---|---|---|
| 1 | 0.34 | Dr. Punjabrao Deshmukh Hostel Subsistence Allowance Scheme | https://dte.maharashtra.gov.in/dr-panjabrao-deshmukh-vastigruh-nirvah-bhatta-yojna | 1 | The Department of Higher and Technical Education, Government of Maharashtra has implemented the “Dr. Panjabrao Deshmukh Vasatigruh Nirvah Bhatta... |
| 2 | 0.31 | Scholarships for Higher Education Abroad to meritorious boys and... | https://dte.maharashtra.gov.in/foreign-scholarship-2022/ | 1 | Benefits to students: Tuition Fee mentioned by the University Full amount of personal health insurance Subsistence Allowance (GBP 9900 for U.K. and... |
| 3 | 0.29 | Scholarship For Top Class Education for Students with Disabilities | https://dte.maharashtra.gov.in/scholarship-for-top-class-education-for-students-with-disabilities | 1 | Desk 1 -Confidential Section Desk 2 -Education Administration and Admission (UG/PG) Desk 3 -Information Technology Cell Desk 4 & 4a -Establishment... |

### Q3. Which documents do I need for MahaDBT?

| Rank | Score | Title | Source | Page | Chunk starts with |
|---|---|---|---|---|---|
| 1 | 0.54 | Scholarship Scheme for Minority Students of the State pursuing Higher... | https://dte.maharashtra.gov.in/scholarship-for-students-of-minority-communities-pursuing-higher-and-professional-courses | 1 | 1) Eligible students studying in the institution can apply online for the above schemes. Maharashtra Government’s MahaDBT Portal (URL –... |
| 2 | 0.52 | Rajarshi Chhatrapati Shahu Maharaj Education Fee Scholarship Scheme | https://dte.maharashtra.gov.in/rajarshi-chhatrapati-shahu-maharaj | 1 | 2 / Scholarship / Up to 8 Lakhs / Professional / Female / 100% / 100% The approval amount of these schemes (in two installments, the first... |
| 3 | 0.52 | Dr. Punjabrao Deshmukh Hostel Subsistence Allowance Scheme | https://dte.maharashtra.gov.in/dr-panjabrao-deshmukh-vastigruh-nirvah-bhatta-yojna | 1 | Total amount / 60,000/- / 51,000/- / 43,000/- / 38,000/- The sanctioned amount of these schemes is deposited to the students in their Aadhaar linked... |

### Q4. Is there an AICTE or NSP scholarship I can apply for?

| Rank | Score | Title | Source | Page | Chunk starts with |
|---|---|---|---|---|---|
| 1 | 0.64 | AICTE - Saksham Scholarship Scheme For Specially Abled Student... | https://scholarships.gov.in/All-Scholarships | 1 | AICTE - Saksham Scholarship Scheme For Specially Abled Student (Technical Degree) (Welfare Based Scheme). Department: All India Council For Technical... |
| 2 | 0.64 | AICTE - Saksham Scholarship Scheme For Specially Abled Student... | https://scholarships.gov.in/All-Scholarships | 1 | AICTE - Saksham Scholarship Scheme For Specially Abled Student (Technical Diploma) (Welfare Based Scheme). Department: All India Council For... |
| 3 | 0.62 | AICTE - Swanath Scholarship Scheme (Technical Degree) (Welfare Based... | https://scholarships.gov.in/All-Scholarships | 1 | AICTE - Swanath Scholarship Scheme (Technical Degree) (Welfare Based Scheme). Department: All India Council For Technical Education. Scheme Open from... |

### Q5. What is the last date to apply this year?

| Rank | Score | Title | Source | Page | Chunk starts with |
|---|---|---|---|---|---|
| 1 | 0.41 | PM-USP – Central Sector Scheme Of Scholarship For College And... | https://scholarships.gov.in/All-Scholarships | 1 | PM-USP – Central Sector Scheme Of Scholarship For College And University Students (CSSS) (Merit Based Scheme). Department: Department of Higher... |
| 2 | 0.40 | National Means Cum Merit Scholarship (Merit Based Scheme) | https://scholarships.gov.in/All-Scholarships | 1 | National Means Cum Merit Scholarship (Merit Based Scheme). Department: Department of School Education & Literacy. Scheme Open from : 01-06-2026... |
| 3 | 0.40 | National Scholarship For Post Graduate Studies (Merit Based Scheme) | https://scholarships.gov.in/All-Scholarships | 1 | National Scholarship For Post Graduate Studies (Merit Based Scheme). Department: UGC. Scheme Open from : 16-09-2026 Student Application Open till :... |

### Q6. What is the hostel fee at Sanjivani College of Engineering?

| Rank | Score | Title | Source | Page | Chunk starts with |
|---|---|---|---|---|---|
| 1 | 0.53 | Scholarship For Top Class Education for Students with Disabilities | https://dte.maharashtra.gov.in/scholarship-for-top-class-education-for-students-with-disabilities | 1 | B) / Miscellaneous/Miscellaneous Allowances i) / Library fees, sports fees, medical examinations and other necessary fees payable by the... |
| 2 | 0.50 | Scholarships for Higher Education Abroad to meritorious boys and... | https://dte.maharashtra.gov.in/foreign-scholarship-2022/ | 1 | Benefits to students: Tuition Fee mentioned by the University Full amount of personal health insurance Subsistence Allowance (GBP 9900 for U.K. and... |
| 3 | 0.48 | Rajarshi Chhatrapati Shahu Maharaj Education Fee Scholarship Scheme | https://dte.maharashtra.gov.in/rajarshi-chhatrapati-shahu-maharaj | 1 | • Scholarship amount – The students / girls are given the following education fees and examination fees for the education fee and examination fee for... |

### Q7. I am a girl studying engineering. Which schemes cover my tuition fee?

| Rank | Score | Title | Source | Page | Chunk starts with |
|---|---|---|---|---|---|
| 1 | 0.61 | Scholarships for Higher Education Abroad to meritorious boys and... | https://dte.maharashtra.gov.in/foreign-scholarship-2022/ | 1 | Benefits to students: Tuition Fee mentioned by the University Full amount of personal health insurance Subsistence Allowance (GBP 9900 for U.K. and... |
| 2 | 0.59 | Scholarship Scheme for Minority Students of the State pursuing Higher... | https://dte.maharashtra.gov.in/scholarship-for-students-of-minority-communities-pursuing-higher-and-professional-courses | 1 | From the academic year 2022-23, the following scholarship amount is provided to the eligible minority students who have come for new scholarship and... |
| 3 | 0.55 | Scholarships for Higher Education Abroad to meritorious boys and... | https://dte.maharashtra.gov.in/foreign-scholarship-2022/ | 1 | Annual family income should be less than Rs.8 lakhs. Age of candidates should not be more than 30 years for Post Graduate course as on 1st July of... |

### Q8. My family income is Rs 6 lakh and I am from an EWS family. Can I get the Rajarshi Chhatrapati Shahu Maharaj scholarship?

| Rank | Score | Title | Source | Page | Chunk starts with |
|---|---|---|---|---|---|
| 1 | 0.78 | Rajarshi Chhatrapati Shahu Maharaj Education Fee Scholarship Scheme | https://dte.maharashtra.gov.in/rajarshi-chhatrapati-shahu-maharaj | 1 | Government of Maharashtra Higher and Technical Education Department, Government, Government subsidized (with government renowned university),... |
| 2 | 0.74 | Rajarshi Chhatrapati Shahu Maharaj Education Fee Scholarship Scheme | https://dte.maharashtra.gov.in/rajarshi-chhatrapati-shahu-maharaj | 1 | • Scholarship amount – The students / girls are given the following education fees and examination fees for the education fee and examination fee for... |
| 3 | 0.73 | Rajarshi Chhatrapati Shahu Maharaj Education Fee Scholarship Scheme | https://dte.maharashtra.gov.in/rajarshi-chhatrapati-shahu-maharaj | 1 | 2 / Scholarship / Up to 8 Lakhs / Professional / Female / 100% / 100% The approval amount of these schemes (in two installments, the first... |

### Q9. How much hostel allowance can I get if my parents are small-land farmers?

| Rank | Score | Title | Source | Page | Chunk starts with |
|---|---|---|---|---|---|
| 1 | 0.46 | Dr. Punjabrao Deshmukh Hostel Subsistence Allowance Scheme | https://dte.maharashtra.gov.in/dr-panjabrao-deshmukh-vastigruh-nirvah-bhatta-yojna | 1 | Quota – Sr.No / Category / Quota for each district of the state 1 / Students whose parents are small land holder farmers or registered laborers. /... |
| 2 | 0.44 | Dr. Punjabrao Deshmukh Hostel Subsistence Allowance Scheme | https://dte.maharashtra.gov.in/dr-panjabrao-deshmukh-vastigruh-nirvah-bhatta-yojna | 1 | Benefit amount (in rupees) Sr.No. / Allowance / Students pursuing higher education in Mumbai city, Mumbai suburbs, Navi Mumbai, Thane, Pune, Pimpri... |
| 3 | 0.37 | Scholarship For Top Class Education for Students with Disabilities | https://dte.maharashtra.gov.in/scholarship-for-top-class-education-for-students-with-disabilities | 1 | C) / Maintenance/Preservation Allowance / Rs. 3,000/- per month for students staying in hostels, Rs. 1,500/- per month for day-scholar students D) /... |

### Q10. I belong to a minority community and my family income is Rs 2 lakh. Which scholarship can I apply for?

| Rank | Score | Title | Source | Page | Chunk starts with |
|---|---|---|---|---|---|
| 1 | 0.72 | Scholarship Scheme for Minority Students of the State pursuing Higher... | https://dte.maharashtra.gov.in/scholarship-for-students-of-minority-communities-pursuing-higher-and-professional-courses | 1 | From the academic year 2022-23, the following scholarship amount is provided to the eligible minority students who have come for new scholarship and... |
| 2 | 0.67 | Scholarship Scheme for Minority Students of the State pursuing Higher... | https://dte.maharashtra.gov.in/scholarship-for-students-of-minority-communities-pursuing-higher-and-professional-courses | 1 | Minority Development Department, Government of Maharashtra has implemented a scholarship scheme for economically weaker, meritorious and minority... |
| 3 | 0.61 | Merit-Cum-Means Scholarship Scheme | https://dte.maharashtra.gov.in/merit-cum-means/ | 1 | Fresh set/quota of scholarships- From the academic year 2022-23, the following scholarship amount is given to eligible minority students who come for... |
