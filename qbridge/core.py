import hashlib
import logging

logger = logging.getLogger(__name__)

async def generate_key(pool) -> str:
    """
    Generate a 256-bit cryptographic key using quantum entropy.
    Pops 16 raw quantum strings (each 16 bits) from the pool, concatenates them, 
    and hashes them using SHA256.
    """
    # Pop 16 of the 16-bit raw strings
    raw_strings = []
    for _ in range(16):
        raw_strings.append(await pool.get_raw_string())
        
    # Concatenate to a single 256-bit string
    concatenated = "".join(raw_strings)
    
    # Hash to output a 256-bit hex string
    hashed_key = hashlib.sha256(concatenated.encode('utf-8')).hexdigest()
    
    return hashed_key
