import type { CrewDetail, Me, Member } from "@/api";

export const ana: Member = {
  id: "11111111-1111-1111-1111-111111111111",
  display_name: "Ana",
  role: "admin",
  rotation_position: 0,
  avatar_seed: "a1b2c3d4",
};

export const bogdan: Member = {
  id: "22222222-2222-2222-2222-222222222222",
  display_name: "Bogdan",
  role: "member",
  rotation_position: 1,
  avatar_seed: "e5f6a7b8",
};

const crew = {
  id: "33333333-3333-3333-3333-333333333333",
  name: "Demo Crew",
  timezone: "Europe/Chisinau",
  proposal_deadline_day: 28,
  reveal_time: "20:00:00",
};

export function meAs(member: Member, language: "ro" | "en" = "en"): Me {
  return {
    user: {
      id: "u-" + member.id,
      username: member.display_name.toLowerCase(),
      preferred_language: language,
    },
    member,
    crew,
    crews: [
      {
        crew_id: crew.id,
        crew_name: crew.name,
        display_name: member.display_name,
        role: member.role,
      },
    ],
  };
}

export const crewDetail: CrewDetail = { ...crew, members: [ana, bogdan] };
