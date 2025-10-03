#!/usr/bin/env python3
"""
Sanctions Data Pipeline - Full Automation
=========================================

One-click automation for the complete sanctions data workflow:
1. Prepare data (AC patterns + vectors)
2. Deploy to Elasticsearch

Interactive menu-driven interface with simple choices.

Usage:
    # Interactive mode (recommended)
    python scripts/sanctions_pipeline.py

    # Full automation (prepare + deploy)
    python scripts/sanctions_pipeline.py --full --es-host localhost:9200

    # Only prepare data
    python scripts/sanctions_pipeline.py --prepare-only

    # Only deploy (use existing prepared data)
    python scripts/sanctions_pipeline.py --deploy-only --es-host localhost:9200
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent


def print_banner():
    """Print welcome banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║        🚀 SANCTIONS DATA PIPELINE                        ║
    ║           Full Automation Workflow                       ║
    ║                                                           ║
    ╟───────────────────────────────────────────────────────────╢
    ║                                                           ║
    ║  Step 1: Prepare Data                                    ║
    ║    • Generate AC patterns (Aho-Corasick)                 ║
    ║    • Generate vector embeddings                          ║
    ║    • Create deployment manifest                          ║
    ║                                                           ║
    ║  Step 2: Deploy to Elasticsearch                         ║
    ║    • Create indices with mappings                        ║
    ║    • Bulk load data                                      ║
    ║    • Warmup queries                                      ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_menu():
    """Print interactive menu"""
    menu = """
    What would you like to do?

    [1] 🔧 Prepare data only (AC patterns + vectors)
    [2] 📤 Deploy to Elasticsearch only (use existing data)
    [3] 🚀 Full pipeline (prepare + deploy)
    [4] ℹ️  Show help
    [5] 🚪 Exit

    """
    print(menu)


def get_choice() -> str:
    """Get user choice"""
    while True:
        choice = input("Enter choice (1-5): ").strip()
        if choice in ['1', '2', '3', '4', '5']:
            return choice
        print("❌ Invalid choice. Please enter 1-5.")


def run_prepare_data(skip_vectors: bool = False) -> bool:
    """Run data preparation script"""
    print("\n" + "="*60)
    print("  🔧 STEP 1: PREPARING DATA")
    print("="*60 + "\n")

    cmd = [
        sys.executable,
        str(project_root / "scripts" / "prepare_sanctions_data.py")
    ]

    if skip_vectors:
        cmd.append("--skip-vectors")

    print(f"Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n✅ Data preparation complete!")
        return True
    else:
        print("\n❌ Data preparation failed!")
        return False


def run_deploy(es_host: Optional[str] = None) -> bool:
    """Run deployment script"""
    print("\n" + "="*60)
    print("  📤 STEP 2: DEPLOYING TO ELASTICSEARCH")
    print("="*60 + "\n")

    cmd = [
        sys.executable,
        str(project_root / "scripts" / "deploy_to_elasticsearch.py")
    ]

    if es_host:
        cmd.extend(["--es-host", es_host])

    print(f"Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n✅ Deployment complete!")
        return True
    else:
        print("\n❌ Deployment failed!")
        return False


def show_help():
    """Show help information"""
    help_text = """
    ╔═══════════════════════════════════════════════════════════╗
    ║  SANCTIONS PIPELINE - HELP                                ║
    ╚═══════════════════════════════════════════════════════════╝

    📁 DATA LOCATION:
       Source files: src/ai_service/data/
       • sanctioned_persons.json
       • sanctioned_companies.json
       • terrorism_black_list.json

    📦 OUTPUT:
       Generated files: output/sanctions/
       • ac_patterns_YYYYMMDD_HHMMSS.json
       • vectors_*.npy
       • deployment_manifest.json

    🔧 STEP 1: PREPARE DATA
       Generates:
       • AC patterns (4 tiers for fuzzy matching)
       • Vector embeddings (384-dim, multilingual)
       • Deployment manifest

    📤 STEP 2: DEPLOY TO ELASTICSEARCH
       • Creates indices with proper mappings
       • Bulk loads AC patterns
       • Runs warmup queries
       • Verifies data

    💡 ELASTICSEARCH CONNECTION:
       Examples:
       • localhost:9200         (Docker local)
       • 192.168.1.100:9200     (Remote server)
       • es.example.com:9200    (Production)

    🔗 MANUAL COMMANDS:
       Prepare only:
         python scripts/prepare_sanctions_data.py

       Deploy only:
         python scripts/deploy_to_elasticsearch.py --es-host localhost:9200

       Full workflow:
         python scripts/sanctions_pipeline.py --full --es-host localhost:9200

    📚 DOCUMENTATION:
       See: docs/SANCTIONS_UPDATE_WORKFLOW.md

    """
    print(help_text)
    input("\nPress Enter to continue...")


def interactive_mode():
    """Run in interactive mode"""
    print_banner()

    while True:
        print_menu()
        choice = get_choice()

        if choice == '1':
            # Prepare data only
            print("\n🔧 Preparing data...")
            skip_vectors = input("\nSkip vector generation (faster)? (y/n): ").strip().lower() == 'y'
            success = run_prepare_data(skip_vectors=skip_vectors)

            if success:
                input("\nPress Enter to continue...")
            else:
                print("\n⚠️  Check errors above")
                input("\nPress Enter to continue...")

        elif choice == '2':
            # Deploy only
            print("\n📤 Deploying to Elasticsearch...")
            print("\nNote: This requires prepared data from Step 1")

            proceed = input("\nHave you already prepared the data? (y/n): ").strip().lower()
            if proceed != 'y':
                print("\n⚠️  Please run Step 1 first (Prepare data)")
                input("\nPress Enter to continue...")
                continue

            success = run_deploy()

            if success:
                input("\nPress Enter to continue...")
            else:
                print("\n⚠️  Check errors above")
                input("\nPress Enter to continue...")

        elif choice == '3':
            # Full pipeline
            print("\n🚀 Running full pipeline...")

            # Step 1: Prepare
            print("\n📋 Starting Step 1: Data Preparation")
            skip_vectors = input("\nSkip vector generation (faster)? (y/n): ").strip().lower() == 'y'

            if not run_prepare_data(skip_vectors=skip_vectors):
                print("\n❌ Pipeline failed at Step 1")
                input("\nPress Enter to continue...")
                continue

            # Step 2: Deploy
            print("\n📋 Starting Step 2: Deployment")

            if not run_deploy():
                print("\n❌ Pipeline failed at Step 2")
                input("\nPress Enter to continue...")
                continue

            # Success
            print("\n" + "="*60)
            print("  ✅ FULL PIPELINE COMPLETE!")
            print("="*60)
            input("\nPress Enter to continue...")

        elif choice == '4':
            # Help
            show_help()

        elif choice == '5':
            # Exit
            print("\n👋 Goodbye!\n")
            sys.exit(0)


def automated_mode(args):
    """Run in automated mode (non-interactive)"""
    if args.full:
        # Full pipeline
        print_banner()
        print("🚀 Running full automated pipeline...\n")

        # Step 1: Prepare
        if not run_prepare_data(skip_vectors=args.skip_vectors):
            print("\n❌ Pipeline failed at Step 1")
            return 1

        # Step 2: Deploy
        if not run_deploy(es_host=args.es_host):
            print("\n❌ Pipeline failed at Step 2")
            return 1

        print("\n" + "="*60)
        print("  ✅ FULL PIPELINE COMPLETE!")
        print("="*60)
        return 0

    elif args.prepare_only:
        # Prepare only
        print_banner()
        if run_prepare_data(skip_vectors=args.skip_vectors):
            return 0
        return 1

    elif args.deploy_only:
        # Deploy only
        print_banner()
        if run_deploy(es_host=args.es_host):
            return 0
        return 1

    else:
        # No mode specified, show help
        print("❌ Please specify a mode: --full, --prepare-only, or --deploy-only")
        print("   Or run without arguments for interactive mode")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Sanctions data pipeline - full automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full pipeline (prepare + deploy)"
    )

    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Only prepare data (AC patterns + vectors)"
    )

    parser.add_argument(
        "--deploy-only",
        action="store_true",
        help="Only deploy to Elasticsearch (requires prepared data)"
    )

    parser.add_argument(
        "--es-host",
        help="Elasticsearch host (e.g., localhost:9200)"
    )

    parser.add_argument(
        "--skip-vectors",
        action="store_true",
        help="Skip vector generation (faster)"
    )

    args = parser.parse_args()

    # Check if any mode is specified
    if args.full or args.prepare_only or args.deploy_only:
        # Automated mode
        exit_code = automated_mode(args)
        sys.exit(exit_code)
    else:
        # Interactive mode
        try:
            interactive_mode()
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            sys.exit(1)


if __name__ == "__main__":
    main()
