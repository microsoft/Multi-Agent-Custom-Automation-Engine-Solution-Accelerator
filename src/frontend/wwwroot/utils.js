
// Utility to generate a SHA-256 hash of a string
window.GenerateHash = async (data) => {
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(JSON.stringify(data)); // Convert the object to a string
    const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer)); // Convert buffer to byte array
    const hashHex = hashArray.map(byte => byte.toString(16).padStart(2, '0')).join('');
    return hashHex; // Return the hash as a hex string
};

// Function to fetch authentication details from EasyAuth
window.GetAuthDetails = async () => {
    // Check if we are running on the server (production environment)
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        // This code runs on the server
        try {
            const authResponse = await fetch('/.auth/me');

            // Check if the request is successful
            if (!authResponse.ok) {
                console.log("Failed to fetch authentication details. Access to chat will be blocked.");
                return null;
            }

            // Parse the response to get user details
            const authData = await authResponse.json();

            // Extract the user details (Azure returns an array, so we pick the first element)
            const userDetails = authData[0] || {};

            // Construct headers using the global config object
            const headers = {
                'Content-Type': 'application/json',
                'X-Ms-Client-Principal': userDetails?.client_principal || '',
                'X-Ms-Client-Principal-Id': userDetails?.user_claims?.find(claim => claim.typ === 'http://schemas.microsoft.com/identity/claims/objectidentifier')?.val || '',
                'X-Ms-Client-Principal-Name': userDetails?.user_claims?.find(claim => claim.typ === 'name')?.val || '',
                'X-Ms-Client-Principal-Idp': userDetails?.identity_provider || '',
            };

            return headers;
        } catch (error) {
            console.error("Error fetching authentication details:", error);
            return null;
        }
    } else {
        // This code runs locally so setup mock headers
        console.log("Running locally. Skipping authentication details fetch.");

        const mockUserDetails = {
            client_principal: 'mock-client-principal-id',
            user_claims: [
              { typ: 'http://schemas.microsoft.com/identity/claims/objectidentifier', val: '12345678-abcd-efgh-ijkl-9876543210ab' }, // Mock Object ID
              { typ: 'name', val: 'Local User' }, // Mock Name
              { typ: 'email', val: 'localuser@example.com' }, // Mock Email (optional claim)
            ],
            identity_provider: 'mock-identity-provider', // Mock Identity Provider
          };
          
          const headers = {
            'Content-Type': 'application/json',
            'X-Ms-Client-Principal': mockUserDetails.client_principal || '',
            'X-Ms-Client-Principal-Id': mockUserDetails.user_claims?.find(claim => claim.typ === 'http://schemas.microsoft.com/identity/claims/objectidentifier')?.val || '',
            'X-Ms-Client-Principal-Name': mockUserDetails.user_claims?.find(claim => claim.typ === 'name')?.val || '',
            'X-Ms-Client-Principal-Idp': mockUserDetails.identity_provider || '',
          };

        return  headers;
    }
};

// window.addEventListener("beforeunload", () => {
//     localStorage.clear();
// });

window.getStoredData = (key)=> {
   return localStorage.getItem(key)
}

window.setStoredData = (key, value)=> {
    localStorage.setItem(key, value)
}

