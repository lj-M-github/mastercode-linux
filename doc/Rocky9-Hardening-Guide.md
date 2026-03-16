
## LinuxHardeningScript

This project focuses on hardening a **Rocky Linux 9** system using best practices aligned with the **CIS Red Hat Enterprise Linux 9 Benchmark – Level 1 (Server)**. The goal is to improve baseline security by patching common misconfigurations, disabling risky defaults, and enforcing stronger system policies.

### Purpose

The idea is to create a reusable and modular way to secure Rocky Linux 9 servers — one that follows real-world hardening guidelines and can be gradually improved over time. The project is designed with practical use in mind, and focuses specifically on a realistic Level 1 compliance target, which is commonly used in enterprise and government environments.

### Approach

- I’m using **OpenSCAP** to scan the system for vulnerabilities and non-compliant settings based on the CIS benchmark.
- Scripts are written in Bash and organized into modules, each targeting a specific security domain (e.g., SSH, firewall, GRUB, PAM).
- So far, the project addresses **high-severity findings only**, but will continue to expand until full Level 1 coverage is reached.

### How to Use

Each script is standalone and can be run individually depending on your needs. You’re free to:
- Execute only the hardening modules relevant to your system
- Or run them all as part of a broader system lockdown

There’s a master script named `secure.sh` that will eventually act as an orchestrator for the entire hardening sequence. It's currently under construction and not yet usable.

### Project Structure (simplified)

```
LinuxHardeningScript/
├── config/                # (optional) Shared settings and thresholds
├── modules/               # Core hardening scripts
│   ├── firewall, SSH, GRUB, SELinux...
│   └── monitoring/        # Log and resource alert scripts
└── secure.sh              # Master runner script (work in progress)
```

---

This is an ongoing project. The goal is to end up with a hardened Rocky Linux 9 system, supported by scripts, evidence of compliance, and clean documentation.