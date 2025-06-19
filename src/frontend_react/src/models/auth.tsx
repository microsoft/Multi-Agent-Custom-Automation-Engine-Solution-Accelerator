export type UserInfo = {
    access_token: string;
    expires_on: string;
    id_token: string;
    provider_name: string;
    user_claims: any[];
    user_email: string;
    user_first_last_name: string;
    user_id: string;
};

export type claim = {
    typ: string;
    val: string;
};