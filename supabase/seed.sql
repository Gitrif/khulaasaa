-- =====================================================================
-- KHULAASAA MALDIVES AGGREGATOR - CANONICAL SEED DATA FOR SUPABASE
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Canonical Sources Registry (Single Source of Truth)
-- ---------------------------------------------------------------------
INSERT INTO sources (slug, name, domain, source_type, logo_url) VALUES
('standard', 'The Standard', 'standard.mv', 'press', '/static/logos/standard.png'),
('sun', 'Sun Online', 'sun.mv', 'press', '/static/logos/sun.png'),
('atolltimes', 'Atoll Times', 'atolltimes.mv', 'press', '/static/logos/atolltimes.svg'),
('dhauru', 'Dhauru', 'dhauru.com', 'press', '/static/logos/dhauru.png'),
('haftha', 'Haftha', 'haftha.mv', 'press', '/static/logos/haftha.png'),
('adhadhu', 'Adhadhu', 'adhadhu.com', 'press', '/static/logos/adhadhu.png'),
('psm', 'PSM News', 'psmnews.mv', 'official', '/static/logos/psm.png'),
('mvcrisis', 'MV Crisis', 't.me/MvCrisis', 'wire', '/static/logos/mvcrisis.svg'),
('mihaaru', 'Mihaaru', 'mihaaru.com', 'press', '/static/logos/mihaaru.png'),
('cnm', 'CNM', 'cnm.mv', 'press', '/static/logos/cnm.png'),
('edition', 'The Edition', 'edition.mv', 'press', '/static/logos/edition.png'),
('avas', 'AVAS', 'avas.mv', 'press', '/static/logos/avas.png'),
('mira', 'MIRA', 'mira.gov.mv', 'official', '/static/logos/mira.png'),
('miadhu', 'Miadhu', 'miadhu.mv', 'press', '/static/logos/miadhu.png'),
('voice', 'Voice', 'voice.mv', 'press', '/static/logos/voice.png'),
('gazette', 'Government Gazette', 'gazette.gov.mv', 'official', '/static/logos/gazette.svg'),
('macl', 'Maldives Airports Company Limited', 'macl.aero', 'portal', '/static/logos/macl.svg'),
('hdc', 'Housing Development Corporation', 'hdc.mv', 'portal', '/static/logos/hdc.svg'),
('mwsc', 'Male'' Water & Sewerage Company', 'mwsc.com.mv', 'portal', '/static/logos/mwsc.svg'),
('stelco', 'State Electric Company Limited', 'stelco.com.mv', 'portal', '/static/logos/stelco.svg'),
('sto', 'State Trading Organization Plc', 'sto.mv', 'portal', '/static/logos/sto.svg'),
('jobcenter', 'JobCenter Maldives', 'jobcenter.mv', 'official', '/static/logos/jobcenter.svg'),
('ibay', 'iBay Maldives', 'ibay.com.mv', 'marketplace', '/static/logos/ibay.png'),
('boahiyaa', 'Boahiyaa Real Estate', 'boahiyaa.com', 'marketplace', '/static/logos/boahiyaa.png'),
('direct', 'Direct Owner / Landlord', NULL, 'marketplace', '/static/logos/direct.svg'),
('kashunamaadhu', 'KashunamaadhuMV', 't.me/KashunamaadhuMV', 'wire', '/static/logos/kashunamaadhu.svg')
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    domain = EXCLUDED.domain,
    source_type = EXCLUDED.source_type,
    logo_url = EXCLUDED.logo_url;

-- ---------------------------------------------------------------------
-- 2. Entities Dictionary (SOEs, Ministries, Councils, Hospitals)
-- ---------------------------------------------------------------------
INSERT INTO entities (slug, name_en, name_dv, entity_type, location, website) VALUES
('housing-development-corporation', 'Housing Development Corporation', 'ހައުސިންގ ޑިވެލޮޕްމަންޓް ކޯޕަރޭޝަން', 'SOE', 'Hulhumale''', 'https://hdc.com.mv'),
('state-trading-organization', 'State Trading Organization Plc', 'ސްޓޭޓް ޓްރޭޑިންގ އޯގަނައިޒޭޝަން', 'SOE', 'Male''', 'https://sto.mv'),
('male-water-and-sewerage-company', 'Male'' Water and Sewerage Company Pvt Ltd', 'މާލޭ ވޯޓަރ އެންޑް ސްވަރޭޖް ކޮމްޕެނީ', 'SOE', 'Male''', 'https://mwsc.com.mv'),
('state-electric-company', 'State Electric Company Limited', 'ސްޓޭޓް އިލެކްޓްރިކް ކޮމްޕެނީ', 'SOE', 'Male''', 'https://stelco.com.mv'),
('fenaka-corporation', 'Fenaka Corporation Limited', 'ފެނަކަ ކޯޕަރޭޝަން ލިމިޓެޑް', 'SOE', 'Male''', 'https://fenaka.mv'),
('maldive-gas', 'Maldive Gas Pvt Ltd', 'މޯލްޑިވް ގޭސް ޕްރައިވެޓް ލިމިޓެޑް', 'SOE', 'Male''', 'https://maldivegas.com'),
('fuel-supplies-maldives', 'Fuel Supplies Maldives Pvt Ltd', 'ފިއުލް ސަޕްލައިސް މޯލްޑިވްސް', 'SOE', 'Male''', 'https://fsm.mv'),
('maldives-transport-and-contracting-company', 'Maldives Transport and Contracting Company Plc', 'މޯލްޑިވްސް ޓްރާންސްޕޯޓް އެންޑް ކޮންޓްރެކްޓިންގ ކޮމްޕެނީ', 'SOE', 'Male''', 'https://mtcc.mv'),
('dhivehi-raajjeyge-gulhun', 'Dhivehi Raajjeyge Gulhun Plc', 'ދިވެހިރާއްޖޭގެ ގުޅުން', 'SOE', 'Male''', 'https://dhiraagu.com.mv'),
('maldives-airports-company', 'Maldives Airports Company Limited', 'މޯލްޑިވްސް އެއަރޕޯޓްސް ކޮމްޕެނީ ލިމިޓެޑް', 'SOE', 'Hulhule', 'https://macl.aero'),
('island-aviation-services', 'Island Aviation Services Limited', 'އައިލެންޑް އޭވިއޭޝަން ސަރވިސަސް', 'SOE', 'Male''', 'https://maldivian.aero'),
('ministry-of-finance', 'Ministry of Finance and Planning', 'މިނިސްޓްރީ އޮފް ފައިނޭންސް', 'Ministry', 'Male''', 'https://finance.gov.mv'),
('ministry-of-planning-housing', 'Ministry of National Planning, Housing and Infrastructure', 'މިނިސްޓްރީ އޮފް ނޭޝަނަލް ޕްލޭނިންގ', 'Ministry', 'Male''', 'https://planning.gov.mv'),
('ministry-of-tourism', 'Ministry of Tourism', 'މިނިސްޓްރީ އޮފް ޓޫރިޒަމް', 'Ministry', 'Male''', 'https://tourism.gov.mv'),
('ministry-of-health', 'Ministry of Health', 'މިނިސްޓްރީ އޮފް ހެލްތު', 'Ministry', 'Male''', 'https://health.gov.mv'),
('ministry-of-education', 'Ministry of Education', 'މިނިސްޓްރީ އޮފް އެޑިޔުކޭޝަން', 'Ministry', 'Male''', 'https://moe.gov.mv'),
('council-male-city', 'Malé City Council', 'މާލެ ސިޓީ ކައުންސިލް', 'Council', 'Male''', 'https://malecity.gov.mv'),
('council-addu-city', 'Addu City Council', 'އައްޑޫ ސިޓީ ކައުންސިލް', 'Council', 'Addu', 'https://adducity.gov.mv'),
('council-fuvahmulah-city', 'Fuvahmulah City Council', 'ފުވައްމުލައް ސިޓީ ކައުންސިލް', 'Council', 'Fuvahmulah', 'https://fuvahmulah.gov.mv'),
('council-kulhudhuffushi-city', 'Kulhudhuffushi City Council', 'ކުޅުދުއްފުށި ސިޓީ ކައުންސިލް', 'Council', 'Kulhudhuffushi', 'https://kulhudhuffushicity.gov.mv'),
('council-uligan', 'Secretariat of the HA. Uligan Council', 'ހއ. އުލިގަމު ކައުންސިލްގެ އިދާރާ', 'Council', 'HA. Uligan', NULL),
('council-eydhafushi', 'Secretariat of the B. Eydhafushi Council', 'ބ. އޭދަފުށި ކައުންސިލްގެ އިދާރާ', 'Council', 'B. Eydhafushi', NULL),
('council-hinnavaru', 'Secretariat of the Lh. Hinnavaru Council', 'ޅ. ހިންނަވަރު ކައުންސިލްގެ އިދާރާ', 'Council', 'Lh. Hinnavaru', NULL),
('council-maafushi', 'Secretariat of the K. Maafushi Council', 'ކ. މާފުށި ކައުންސިލްގެ އިދާރާ', 'Council', 'K. Maafushi', NULL),
('council-dhangethi', 'Secretariat of the ADh. Dhangethi Council', 'އދ. ދަނގެތި ކައުންސިލްގެ އިދާރާ', 'Council', 'ADh. Dhangethi', NULL),
('council-felidhoo', 'Secretariat of the V. Felidhoo Council', 'ވ. ފެލިދޫ ކައުންސިލްގެ އިދާރާ', 'Council', 'V. Felidhoo', NULL),
('council-kolhufushi', 'Secretariat of the M. Kolhufushi Council', 'މ. ކޮޅުފުށި ކައުންސިލްގެ އިދާރާ', 'Council', 'M. Kolhufushi', NULL),
('council-nilandhoo', 'Secretariat of the F. Nilandhoo Council', 'ފ. ނިލަންދޫ ކައުންސިލްގެ އިދާރާ', 'Council', 'F. Nilandhoo', NULL),
('council-kudahuvadhoo', 'Secretariat of the Dh. Kudahuvadhoo Council', 'ދ. ކުޑަހުވަދޫ ކައުންސިލްގެ އިދާރާ', 'Council', 'Dh. Kudahuvadhoo', NULL),
('council-timarafushi', 'Secretariat of the Th. Timarafushi Council', 'ތ. ތިމަރަފުށި ކައުންސިލްގެ އިދާރާ', 'Council', 'Th. Timarafushi', NULL),
('maldives-polytechnic', 'Maldives Polytechnic', 'މޯލްޑިވްސް ޕޮލިޓެކްނިކް', 'Education', 'Male''', 'https://polytechnic.edu.mv'),
('maldives-customs-service', 'Maldives Customs Service', 'މޯލްޑިވްސް ކަސްޓަމްސް ސަރވިސް', 'Independent', 'Male''', 'https://customs.gov.mv'),
('igmh', 'Indira Gandhi Memorial Hospital', 'އިންދިރާ ގާންދީ މެމޯރިއަލް ހޮސްޕިޓަލް', 'Healthcare', 'Male''', 'https://igmh.gov.mv'),
('mira', 'Maldives Inland Revenue Authority', 'މޯލްޑިވްސް އިންލަންޑް ރެވެނިއު އޮތޯރިޓީ', 'Independent', 'Male''', 'https://mira.gov.mv')
ON CONFLICT (slug) DO NOTHING;
