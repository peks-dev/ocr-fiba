"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { deleteRosterPlayer, readClubStore, upsertRosterPlayer, writeClubStore } from "./storage";
import type { ClubPlayer, ClubStore } from "./types";
import { EmptyState, Panel } from "./ui";

const INITIAL_STORE: ClubStore = { clubName: "My Club", roster: [], games: [] };

export function RosterClient() {
  const [store, setStore] = useState<ClubStore>(INITIAL_STORE);
  const [name, setName] = useState("");
  const [number, setNumber] = useState("");
  const [position, setPosition] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editNumber, setEditNumber] = useState("");
  const [isBooting, setIsBooting] = useState(true);

  useEffect(() => {
    setStore(readClubStore());
    setIsBooting(false);
  }, []);

  const sortedRoster = useMemo(
    () => [...store.roster].sort((a, b) => a.name.localeCompare(b.name) || Number(a.number) - Number(b.number)),
    [store.roster],
  );

  function persist(next: ClubStore) {
    setStore(next);
    writeClubStore(next);
  }

  function saveClubName(value: string) {
    const next = { ...store, clubName: value || "My Club" };
    persist(next);
  }

  function addPlayer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanName = name.trim();
    const cleanNumber = number.trim().replace(/^0+(?=\d)/, "");
    if (!cleanName || !cleanNumber) {
      toast.error("Add player name and jersey number.");
      return;
    }
    const duplicate = store.roster.some((player) => player.name.trim().toLowerCase() === cleanName.toLowerCase());
    if (duplicate) {
      toast.error(`${cleanName} is already in your roster.`);
      return;
    }
    const player: ClubPlayer = {
      id: `player:${cleanNumber}:${Date.now()}`,
      name: cleanName,
      number: cleanNumber,
      position: position.trim() || undefined,
      createdAt: new Date().toISOString(),
    };
    persist(upsertRosterPlayer(store, player));
    setName("");
    setNumber("");
    setPosition("");
    toast.success("Player added to roster.");
  }

  function startEditing(player: ClubPlayer) {
    setEditingId(player.id);
    setEditName(player.name);
    setEditNumber(player.number);
  }

  function saveEdit(player: ClubPlayer) {
    const cleanName = editName.trim();
    const cleanNumber = editNumber.trim().replace(/^0+(?=\d)/, "");
    if (!cleanName) {
      toast.error("Player name is required.");
      return;
    }
    const nextPlayer = { ...player, name: cleanName, number: cleanNumber || player.number };
    persist(upsertRosterPlayer(store, nextPlayer));
    setEditingId(null);
    toast.success("Player profile updated.");
  }

  function removePlayer(playerId: string) {
    persist(deleteRosterPlayer(store, playerId));
    toast.success("Player removed from roster.");
  }

  if (isBooting) return <Panel className="p-6 text-muted">Loading roster...</Panel>;

  return (
    <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      <Panel className="h-fit p-5 sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep">Club setup</p>
        <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Roster from OCR</h2>
        <p className="mt-2 text-sm leading-6 text-muted">Your roster is created automatically from scanned sheets by matching player names, not jersey numbers. Use manual add only for players who have not appeared in an extraction yet, or edit names to set the canonical version.</p>

        <label className="mt-5 block">
          <span className="text-[0.65rem] font-semibold uppercase tracking-wide text-faint">Club name</span>
          <input
            value={store.clubName}
            onChange={(event) => saveClubName(event.target.value)}
            className="mt-1 w-full rounded-field border border-border bg-surface px-3 py-3 text-base text-ink outline-none transition focus:border-primary"
          />
        </label>

        <form onSubmit={addPlayer} className="mt-5 space-y-3 rounded-card border border-border bg-elevated p-4">
          <p className="text-sm font-semibold text-ink">Add missing player manually</p>
          <div className="grid grid-cols-[0.45fr_1fr] gap-3">
            <label>
              <span className="text-[0.65rem] font-semibold uppercase tracking-wide text-faint">#</span>
              <input
                value={number}
                onChange={(event) => setNumber(event.target.value)}
                inputMode="numeric"
                className="mt-1 w-full rounded-field border border-border bg-surface px-3 py-3 text-ink outline-none transition focus:border-primary"
              />
            </label>
            <label>
              <span className="text-[0.65rem] font-semibold uppercase tracking-wide text-faint">Name</span>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="mt-1 w-full rounded-field border border-border bg-surface px-3 py-3 text-ink outline-none transition focus:border-primary"
              />
            </label>
          </div>
          <label className="block">
            <span className="text-[0.65rem] font-semibold uppercase tracking-wide text-faint">Position / role optional</span>
            <input
              value={position}
              onChange={(event) => setPosition(event.target.value)}
              placeholder="Guard, forward, captain..."
              className="mt-1 w-full rounded-field border border-border bg-surface px-3 py-3 text-ink outline-none transition focus:border-primary"
            />
          </label>
          <button type="submit" className="w-full rounded-field bg-primary px-4 py-3 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85">
            Add missing player
          </button>
        </form>
      </Panel>

      <Panel className="p-5 sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep">Roster</p>
            <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">{store.clubName}</h2>
          </div>
          <span className="rounded-full bg-elevated px-3 py-1 text-xs font-semibold text-muted">{sortedRoster.length} players</span>
        </div>

        {sortedRoster.length === 0 ? (
          <div className="mt-6">
            <EmptyState title="No players yet" description="Scan your first scoresheet from Capture. After you choose team A or B, detected players will appear here automatically." />
          </div>
        ) : (
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {sortedRoster.map((player) => {
              const editing = editingId === player.id;
              return (
                <div key={player.id} className="rounded-card border border-border bg-elevated p-4">
                  {editing ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-[0.45fr_1fr] gap-3">
                        <label>
                          <span className="text-[0.65rem] font-semibold uppercase tracking-wide text-faint">Current #</span>
                          <input
                            value={editNumber}
                            onChange={(event) => setEditNumber(event.target.value)}
                            inputMode="numeric"
                            className="mt-1 w-full rounded-field border border-border bg-surface px-3 py-2 text-ink outline-none transition focus:border-primary"
                          />
                        </label>
                        <label>
                          <span className="text-[0.65rem] font-semibold uppercase tracking-wide text-faint">Canonical name</span>
                          <input
                            value={editName}
                            onChange={(event) => setEditName(event.target.value)}
                            className="mt-1 w-full rounded-field border border-border bg-surface px-3 py-2 text-ink outline-none transition focus:border-primary"
                          />
                        </label>
                      </div>
                      <div className="flex gap-2">
                        <button type="button" onClick={() => saveEdit(player)} className="rounded-full bg-primary px-3 py-1.5 text-xs font-semibold text-primary-contrast">Save name</button>
                        <button type="button" onClick={() => setEditingId(null)} className="rounded-full border border-border px-3 py-1.5 text-xs font-semibold text-muted">Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-semibold text-ink">{player.name}</p>
                        <p className="mt-1 text-xs text-muted">Current # {player.number || "n/d"} · {player.position || "No role set"}</p>
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <button type="button" onClick={() => startEditing(player)} className="rounded-full border border-border px-3 py-1 text-xs font-semibold text-muted transition hover:border-primary hover:text-ink">
                          Edit
                        </button>
                        <button type="button" onClick={() => removePlayer(player.id)} className="rounded-full border border-border px-3 py-1 text-xs font-semibold text-muted transition hover:border-danger hover:text-danger">
                          Remove
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );
}
