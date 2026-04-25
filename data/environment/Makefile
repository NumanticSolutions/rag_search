# --- Configuration ---
ENV_NAME = rag-search
YAML_FILE = environment_rag_search.yml

# --- Primary Targets ---

# Default: Builds the environment and installs browsers
setup: clean create-env

# Create or update the conda environment (includes awscli and google-cloud-sdk)
create-env:
	conda env create -f $(YAML_FILE) || conda env update -f $(YAML_FILE) --prune


# --- Cleanup ---
clean:
	conda remove --name $(ENV_NAME) --all -y || echo "Environment not found, skipping clean."

# --- Documentation ---

help:
	@echo ""
	@echo "Available commands:"
	@echo "  make setup              Clean and recreate the environment"
	@echo "  make create-env         Create the environment"
	@echo "  make clean              Delete the Conda environment"
	@echo "  make help               Show this help message"
	@echo ""