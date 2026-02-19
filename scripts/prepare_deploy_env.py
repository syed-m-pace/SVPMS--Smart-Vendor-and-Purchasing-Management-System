import os
import yaml

def parse_env_file(filepath):
    env_vars = {}
    if not os.path.exists(filepath):
        return env_vars
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Split by first =
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                env_vars[key] = value
    return env_vars

def main():
    env_vars = parse_env_file('.env')
    
    # Overrides for production
    env_vars['ENVIRONMENT'] = 'production'
    from datetime import datetime
    env_vars['APP_VERSION'] = datetime.now().strftime("%Y%m%d")

    # Add Vercel URL to CORS_ORIGINS for production
    vercel_url = "https://svpms-smart-vendor-and-purchasing-m.vercel.app"
    if 'CORS_ORIGINS' in env_vars:
        if vercel_url not in env_vars['CORS_ORIGINS']:
            env_vars['CORS_ORIGINS'] += f",{vercel_url}"
    else:
        env_vars['CORS_ORIGINS'] = vercel_url

    # Remove PORT as Cloud Run injects it
    if 'PORT' in env_vars:
        del env_vars['PORT']

    # Write to env.yaml
    with open('env.yaml', 'w') as f:
        yaml.dump(env_vars, f, default_flow_style=False)
    
    print("Generated env.yaml from .env with production overrides.")

if __name__ == "__main__":
    main()
