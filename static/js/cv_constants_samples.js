
// Standard Constants (mirrored from backend)
const STANDARD_LANGUAGES = [
  "English", "Dhivehi", "Arabic", "Hindi", "Urdu", "Sinhala", "Bengali", "Malayalam", "Tamil", "French", "Russian", "Chinese", "German"
];
const LANGUAGE_PROFICIENCIES = [
  "Native / Bilingual (މާދަރީ ބަސް)",
  "Fluent / Full Professional",
  "Professional Working",
  "Intermediate / Conversational",
  "Elementary / Basic"
];
const EDUCATION_LEVELS = [
  "Primary School",
  "Secondary / O-Level",
  "Higher Secondary / A-Level",
  "Certificate / Diploma",
  "Advanced Diploma",
  "Undergraduate / Bachelor's Degree",
  "Postgraduate Diploma",
  "Master's Degree",
  "PhD / Doctorate"
];
const STANDARD_INSTITUTIONS = [
  "The Maldives National University (MNU)",
  "Villa College",
  "Cyryx College",
  "MAPS College",
  "Avid College",
  "Islamic University of Maldives (IUM)",
  "Center for Higher Secondary Education (CHSE)",
  "Majeediyya School",
  "Aminiya School",
  "Dharumavantha School",
  "Ahmadhiyya International School",
  "Kalaafaanu School",
  "Maldives Polytechnic",
  "Other / Overseas University"
];

// Sample CV Datasets using realistic fictional dummy Maldivian profiles
const SAMPLES = {
  sample1: {
    fullName: "Ahmed Naseem",
    nationalId: "A000000",
    dob: "15th March 1993",
    sex: "Male",
    nationality: "Maldivian",
    address: "H. Dhunfini, Male’, Rep. of Maldives.",
    email: "ahmed.naseem.demo@example.mv",
    phone: "+960 700 0001",
    photoUrl: "",
    summary: "Reliable, motivated, and safety-conscious transport and logistics professional with extensive driving experience across Greater Malé and airport corridors. Skilled in vehicle fleet coordination, passenger hospitality, store operations, and client service.",
    skills: [
      "Defensive Driving & Safe Passenger Transport (B1/B2)",
      "Vehicle Dispatch & Route Scheduling",
      "Store Inventory & POS Cash Reconciliation",
      "Customer Service & Luggage Handling"
    ],
    experience: [
      {
        role: "Fleet Driver & Logistics Assistant",
        company: "Island Logistics & Transport Services",
        fromDate: "Jun 2023",
        toDate: "",
        isCurrent: true,
        description: "• Safely transport VIP guests, tourists, and staff across Malé and Hulhumalé.\n• Conduct daily vehicle inspections, routine maintenance logs, and fuel management."
      },
      {
        role: "Store Operations Assistant",
        company: "Raajje Retail Enterprises",
        fromDate: "Nov 2021",
        toDate: "May 2023",
        isCurrent: false,
        description: "• Managed stock replenishment, inventory receiving, and customer billing.\n• Reconciled shift sales and maintained floor display standards."
      }
    ],
    education: [
      {
        level: "Secondary / O-Level",
        institution: "Dharumavantha School",
        customInstitution: "",
        degree: "Cambridge GCE O-Level",
        grade: "Completed",
        fromDate: "Jan 2008",
        toDate: "Nov 2010",
        isCurrent: false
      }
    ],
    certifications: [
      {
        title: "Maldivian Driving License (B1/B2/C1)",
        issuer: "Ministry of Transport & Civil Aviation",
        year: "2019",
        credentialId: "MV-LIC-000000"
      }
    ],
    training: "• Defensive Driving & Road Safety Workshop (Maldives Police Service, 2022)\n• Basic First Aid & Fire Safety Certification",
    languages: [
      { language: "Dhivehi", proficiency: "Native / Bilingual (މާދަރީ ބަސް)" },
      { language: "English", proficiency: "Professional Working" }
    ],
    portfolio: [],
    referees: [
      {
        name: "Ibrahim Rasheed",
        designation: "Operations Manager",
        company: "Island Logistics Ltd",
        contact: "+960 700 9001"
      }
    ]
  },
  sample2: {
    fullName: "Mariyam Zoya",
    nationalId: "A111111",
    dob: "20th August 1988",
    sex: "Female",
    nationality: "Maldivian",
    address: "M. Orchid Villa, Male’, Rep. of Maldives.",
    email: "mariyam.zoya.demo@example.mv",
    phone: "+960 700 0002",
    photoUrl: "",
    summary: "Accomplished Executive Administrator and Media Coordinator with over 12 years of experience in corporate correspondence, document workflows, and event communications. Expert in liaising with ministries, SOEs, and corporate stakeholders.",
    skills: [
      "Executive Administration & Ministry Correspondence",
      "Official Thaana & English Business Writing",
      "Records Management & Procurement Coordination",
      "Event Planning, Protocol & Public Relations"
    ],
    experience: [
      {
        role: "Senior Executive Officer",
        company: "Horizon Communications Group",
        fromDate: "Jan 2018",
        toDate: "",
        isCurrent: true,
        description: "• Manage executive schedules, high-level council memos, and official gazette notices.\n• Coordinate vendor quotations, procurement bidding processes, and meeting minutes."
      },
      {
        role: "Office Administrator",
        company: "Maldives Marine Trade Solutions",
        fromDate: "Jan 2012",
        toDate: "Dec 2017",
        isCurrent: false,
        description: "• Supervised daily front-office operations, client billing, and staff travel.\n• Maintained registry of regulatory permits and tender compliance submissions."
      }
    ],
    education: [
      {
        level: "Bachelor's Degree",
        institution: "The Maldives National University (MNU)",
        customInstitution: "",
        degree: "Bachelor of Business Administration (BBA)",
        grade: "First Class",
        fromDate: "2008",
        toDate: "2011",
        isCurrent: false
      }
    ],
    certifications: [
      {
        title: "Certified Administrative Professional (CAP)",
        issuer: "Maldives Institute of Technology",
        year: "2016",
        credentialId: "MIT-CAP-2016"
      }
    ],
    training: "• Government Procurement Regulations & Tender Procedures (2020)\n• Advanced Thaana Document Processing (NCIT)",
    languages: [
      { language: "Dhivehi", proficiency: "Native / Bilingual (މާދަރީ ބަސް)" },
      { language: "English", proficiency: "Fluent / Full Professional" }
    ],
    portfolio: [
      {
        title: "Annual Stakeholder Summit & Gala",
        role: "Event Director",
        url: "https://example.mv/events",
        description: "Planned and delivered nationwide 3-day industry conference with 400+ delegates."
      }
    ],
    referees: [
      {
        name: "Aishath Waheeda",
        designation: "Managing Director",
        company: "Horizon Group Pvt Ltd",
        contact: "+960 700 9002"
      }
    ]
  },
  sample3: {
    fullName: "Hassan Rasheed",
    nationalId: "A222222",
    dob: "10th December 1985",
    sex: "Male",
    nationality: "Maldivian",
    address: "Ma. Green Waves, Male’, Rep. of Maldives.",
    email: "hassan.rasheed.demo@example.mv",
    phone: "+960 700 0003",
    photoUrl: "",
    summary: "Dynamic and service-focused Guest Relations and Airport Operations Manager with over 15 years in luxury resort hospitality and aviation transfers. Proven track record managing CIP/VIP lounges, seaplane transfer coordination, and multicultural guest-facing teams.",
    skills: [
      "Ultra-Luxury Guest Relations & VIP/CIP Etiquette",
      "Airport Lounge & Seaplane Flight Coordination (MACL/TMA)",
      "Standard Operating Procedures (SOP) & Quality Assurance",
      "Team Leadership, Rostering & Hospitality Training"
    ],
    experience: [
      {
        role: "Airport Operations & Guest Services Manager",
        company: "Coral Breeze Resort Collection",
        fromDate: "Jan 2019",
        toDate: "",
        isCurrent: true,
        description: "• Lead terminal operations at Velana International Airport for arriving resort guests.\n• Liaise directly with TMA, MACL, customs, and immigration for seamless luggage transfers.\n• Supervise VIP lounge concierge and speedboat departure schedules."
      },
      {
        role: "Assistant Front Office Manager",
        company: "Lagoon Sands Maldives Resort",
        fromDate: "Mar 2012",
        toDate: "Dec 2018",
        isCurrent: false,
        description: "• Managed arrival briefings, villa check-ins, and guest excursions.\n• Maintained 96%+ positive guest feedback score across online travel ratings."
      }
    ],
    education: [
      {
        level: "Certificate / Diploma",
        institution: "Faculty of Hospitality & Tourism Studies (MNU)",
        customInstitution: "",
        degree: "Diploma in Hospitality & Tourism Management",
        grade: "Distinction",
        fromDate: "2004",
        toDate: "2006",
        isCurrent: false
      }
    ],
    certifications: [
      {
        title: "Certified Hospitality Supervisor (CHS)",
        issuer: "American Hotel & Lodging Educational Institute",
        year: "2015",
        credentialId: "AHLEI-CHS-2015"
      }
    ],
    training: "• Aviation Safety & Airport Ramp Operations Security\n• Food Hygiene and HACCP Principles (2018)",
    languages: [
      { language: "Dhivehi", proficiency: "Native / Bilingual (މާދަރީ ބަސް)" },
      { language: "English", proficiency: "Fluent / Full Professional" }
    ],
    portfolio: [
      {
        title: "Private Seaplane Lounge Service Design",
        role: "Project Manager",
        url: "https://example.mv/lounge",
        description: "Established dedicated private lounge facility and baggage tracking system."
      }
    ],
    referees: [
      {
        name: "Mohamed Solih",
        designation: "Director of Operations",
        company: "Coral Breeze Resorts",
        contact: "+960 700 9003"
      }
    ]
  }
};

// Aliases for backward compatibility
SAMPLES.shifau = SAMPLES.sample1;
SAMPLES.zeenath = SAMPLES.sample2;
SAMPLES.simah = SAMPLES.sample3;

// Initial Setup
document.addEventListener("DOMContentLoaded", async function() {
  if (currentUser) {
    loadUserSavedCv();
  } else {
    loadSampleCv("shifau");
  }
});

// Load saved CV from server
async function loadUserSavedCv() {
  try {
    const res = await fetch("/api/cv");
    if (res.ok) {
      const data = await res.json();
      if (data && data.cv && data.cv.data && Object.keys(data.cv.data).length > 0) {
        populateFormFromData(data.cv.data);
        if (data.cv.template) {
          selectTemplate(data.cv.template, true);
        }
        document.getElementById("saveStatus").textContent = "Loaded from account";
        return;
      }
    }
  } catch(e) {}
  loadSampleCv("shifau");
}

