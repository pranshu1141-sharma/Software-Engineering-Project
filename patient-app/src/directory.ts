export type CareListing = {
  id: string;
  kind: 'Doctor' | 'Hospital' | 'Clinic';
  name: string;
  specialties: string[];
  address: string;
  locality: string;
  city: string;
  phone: string | null;
  website: string;
  affiliation: string | null;
  description: string;
  sources: { title: string; url: string }[];
  checked_at: string;
};
export type CareDirectory = {
  region: string | null;
  location_basis: string;
  listings: CareListing[];
};
export const EMPTY_DIRECTORY: CareDirectory = { region: null, location_basis: 'Location needed', listings: [] };
export const mapsUrl = (item: CareListing) => `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${item.name}, ${item.address}, ${item.city}`)}`;
