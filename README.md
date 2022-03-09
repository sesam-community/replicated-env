# Replicated env

Script that rewrites the input pipes to replicate data from a source instance instead of fetching the data again from the real input systems.

Add a admin JWT to the source and target instance. Run script with the required environment variables listed in the beginning of the script.

For improved security create a custom role in the source instance, give the role "Endpoint read data" rights on the pipe prototype. Make a JWT for that role, and set the "UPSTREAM_SYSTEM_JWT" environment variable in the script to the new jwt.

Typically set up as a periodic job.

Note that the script does not support transforms yet.
