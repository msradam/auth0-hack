-- Seed data for development/staging environment
-- WARNING: This contains real beneficiary data copied from production
-- TODO: Replace with synthetic data before merging to main

INSERT INTO beneficiaries (unhcr_case, name, dob, phone, location, medical, ethnicity) VALUES
('123-45C00891', 'Ahmad Al-Hassan', '1985-03-12', '+962-79-555-1234', 'Za''atari Camp, Block 4, Shelter 17', 'PTSD, chronic back pain', 'Sunni Arab'),
('123-45C00892', 'Fatima Nour', '1992-07-22', '+962-79-555-5678', 'Za''atari Camp, Block 7, Shelter 3', 'Pregnant, high-risk, HIV positive', 'Kurdish'),
('123-45C00893', 'Omar Khalid', '1978-11-03', '+962-79-555-9012', 'Azraq Camp, Village 3', 'Tuberculosis treatment', 'Yazidi');

INSERT INTO staff (name, role, phone, email, location) VALUES
('Khaled Mahmoud', 'Field Officer', '+962-79-555-9012', 'k.mahmoud@ngo-example.org', 'Za''atari'),
('Rania Sayed', 'Case Worker', '+962-79-555-3456', 'r.sayed@ngo-example.org', 'Azraq');

-- Grant admin access to new contractor
GRANT ALL PRIVILEGES ON beneficiary_registry.* TO 'contractor_audit'@'%';
