export interface User {
  id: number;
  full_name: string;
  username: string;
  mobile_no: string;
  email?: string;
  user_code?: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
}

export interface Player {
  id: number;
  name: string;
  phone?: string;
  batting_style?: string;
  bowling_style?: string;
  user_id?: string;
  code?: string;
}

export interface Team {
  id: number;
  name: string;
  location?: string;
  captain_id?: number;
  members?: Player[];
}

export interface Tournament {
  id: number;
  name: string;
  format: 'round_robin' | 'knockout' | 'groups';
  rules?: any;
  team_ids?: number[];
  status: string;
  teams?: Team[];
  standings?: Array<{
    team_id: number;
    name: string;
    played: number;
    won: number;
    lost: number;
    tied: number;
    points: number;
    nrr: number;
  }>;
  fixtures?: Array<{
    id: number;
    round: number;
    team_a_id?: number;
    team_b_id?: number;
    team_a_name?: string;
    team_b_name?: string;
    match_id?: number;
    status: string;
    winner_team_id?: number;
  }>;
  champion?: Team;
}

export interface MatchState {
  id: number;
  team_a: string;
  team_b: string;
  bat_first: string;
  format_id: string;
  rules_name?: string;
  current_innings: number;
  second_innings_started: boolean;
  pending_bowler?: string;
  result?: string;
  status: 'in_progress' | 'completed' | 'abandoned';
  stream_url?: string;
  meta?: {
    venue?: string;
    tournament?: string;
    match_no?: string;
    toss_winner?: string;
    toss_decision?: string;
  };
  squad_a?: string[];
  squad_b?: string[];
  innings: Array<{
    innings_number: number;
    batting_team: string;
    bowling_team: string;
    runs: number;
    wickets: number;
    legal_balls: number;
    overs_str: string;
    result_note?: string;
    striker?: string;
    non_striker?: string;
    current_bowler?: string;
    batting_card: Array<{
      player: string;
      runs: number;
      balls: number;
      fours: number;
      sixes: number;
      dismissal?: string;
      is_out: boolean;
      strike_rate: number;
    }>;
    bowling_card: Array<{
      player: string;
      overs_str: string;
      runs: number;
      wickets: number;
      wides: number;
      no_balls: number;
      economy: number;
    }>;
    recent_balls: Array<{
      runs_off_bat: number;
      is_wide: boolean;
      is_no_ball: boolean;
      is_wicket: boolean;
      summary: string;
      shot_zone?: string;
    }>;
  }>;
}
