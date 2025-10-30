export type Role = "user" | "assistant";

export type Message = {
  role: Role;
  content: string;
};

export const COLOR_PRIMARY = "#58d2e4ff"; 
