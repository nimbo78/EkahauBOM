/**
 * Note models for displaying Ekahau map notes
 */

export interface Note {
  id: string;
  text: string;
  created_at: string;
  created_by: string;
  image_ids: string[];
  status: string;
}

export interface PictureNoteLocation {
  floor_plan_id: string;
  floor_name: string;
  x: number;
  y: number;
}

export interface PictureNote {
  id: string;
  location?: PictureNoteLocation;
  note_ids: string[];
  status: string;
}

export interface CableNotePoint {
  x: number;
  y: number;
}

export interface CableNote {
  id: string;
  floor_plan_id: string;
  floor_name: string;
  points: CableNotePoint[];
  color: string;
  note_ids: string[];
  status: string;
}

export interface NotesSummary {
  total_text_notes: number;
  total_cable_notes: number;
  total_picture_notes: number;
}

export interface NotesData {
  project_id: string;
  text_notes: Note[];
  cable_notes: CableNote[];
  picture_notes: PictureNote[];
  summary: NotesSummary;
}
