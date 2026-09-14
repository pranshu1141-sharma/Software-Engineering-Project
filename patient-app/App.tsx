import React, { useEffect, useRef, useState } from "react";
import { StatusBar } from "expo-status-bar";
import {
  ActivityIndicator,
  BackHandler,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from "react-native";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Check,
  ChevronRight,
  HeartPulse,
  Home,
  Info,
  MapPin,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Ticket,
  UserRound,
  X,
} from "lucide-react-native";
import {
  api,
  Appointment,
  newRequestId,
  Provider,
  Queue,
  Slot,
} from "./src/api";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";

const C = {
  green: "#247C70",
  ink: "#193B3A",
  muted: "#738783",
  mint: "#EAF5F0",
  bg: "#F6F8F4",
  line: "#E1EAE5",
};
type Screen =
  | "home"
  | "symptoms"
  | "guidance"
  | "doctors"
  | "doctor"
  | "confirmed"
  | "appointments"
  | "queue"
  | "about";
const date = (value: string) =>
  new Date(value).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    timeZone: "Asia/Kolkata",
  });
const time = (value: string) =>
  new Date(value).toLocaleTimeString("en-IN", {
    hour: "numeric",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  });
const status = (value: string) =>
  ({
    booked: "Upcoming",
    checked_in: "In queue",
    ready: "Your turn",
    completed: "Completed",
    cancelled: "Cancelled",
  })[value] || value;
function Button({
  title,
  onPress,
  secondary = false,
  disabled = false,
  busy = false,
}: {
  title: string;
  onPress: () => void;
  secondary?: boolean;
  disabled?: boolean;
  busy?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={title}
      disabled={disabled || busy}
      onPress={onPress}
      style={({ pressed }) => [
        s.button,
        secondary && s.secondary,
        (disabled || busy) && { opacity: 0.5 },
        pressed && { opacity: 0.8 },
      ]}
    >
      {busy ? (
        <ActivityIndicator color={secondary ? C.green : "#fff"} />
      ) : (
        <>
          <Text style={[s.buttonText, secondary && { color: C.green }]}>
            {title}
          </Text>
          <ArrowRight size={18} color={secondary ? C.green : "#fff"} />
        </>
      )}
    </Pressable>
  );
}
function Note({ text }: { text: string }) {
  return (
    <View style={s.note}>
      <ShieldCheck size={18} color={C.green} />
      <Text style={s.noteText}>{text}</Text>
    </View>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <SafeAreaView style={{ flex: 1, backgroundColor: "#FFFFFF" }}>
        <PatientApp />
      </SafeAreaView>
    </SafeAreaProvider>
  );
}
function PatientApp() {
  const wide = useWindowDimensions().width > 850;
  const [screen, setScreen] = useState<Screen>("home");
  const [doctors, setDoctors] = useState<Provider[]>([]),
    [visits, setVisits] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [refreshing, setRefreshing] = useState(false),
    [error, setError] = useState("");
  const [symptoms, setSymptoms] = useState(""),
    [suggestions, setSuggestions] = useState<string[]>([]),
    [filter, setFilter] = useState("All"),
    [query, setQuery] = useState("");
  const [doctor, setDoctor] = useState<Provider | null>(null),
    [slots, setSlots] = useState<Slot[]>([]),
    [slot, setSlot] = useState(""),
    [slotsLoading, setSlotsLoading] = useState(false);
  const [confirmed, setConfirmed] = useState<Appointment | null>(null),
    [activeId, setActiveId] = useState<string | null>(null),
    [queue, setQueue] = useState<Queue | null>(null),
    [desk, setDesk] = useState(false),
    [cancelId, setCancelId] = useState<string | null>(null);
  const bookingKey = useRef(newRequestId()),
    scroll = useRef<ScrollView>(null);
  const go = (next: Screen) => {
    setError("");
    setScreen(next);
    scroll.current?.scrollTo({ y: 0, animated: false });
  };
  const back = () =>
    go(
      screen === "doctor"
        ? "doctors"
        : screen === "guidance"
          ? "symptoms"
          : "home",
    );
  async function load() {
    try {
      const [p, a] = await Promise.all([
        api<{ providers: Provider[] }>("/api/providers"),
        api<{ appointments: Appointment[] }>("/api/appointments"),
      ]);
      setDoctors(p.providers);
      setVisits(a.appointments);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }
  const loadVisits = async () =>
    setVisits(
      (await api<{ appointments: Appointment[] }>("/api/appointments"))
        .appointments,
    );
  useEffect(() => {
    void load();
  }, []);
  useEffect(() => {
    if (Platform.OS === "web") return;
    const sub = BackHandler.addEventListener("hardwareBackPress", () => {
      if (screen === "home") return false;
      back();
      return true;
    });
    return () => sub.remove();
  }, [screen]);
  const current =
    visits.find((v) => ["checked_in", "ready"].includes(v.status)) ||
    visits.find((v) => v.status === "booked");
  const selectedVisit = visits.find((v) => v.id === activeId) || current;
  useEffect(() => {
    setQueue(null);
    if (
      screen !== "queue" ||
      !selectedVisit ||
      !["checked_in", "ready", "completed"].includes(selectedVisit.status)
    )
      return;
    let alive = true;
    const poll = async () => {
      try {
        const q = await api<Queue>(
          `/api/appointments/${selectedVisit.id}/queue`,
        );
        if (alive) {
          setQueue(q);
          setError("");
        }
      } catch (e: any) {
        if (alive) setError(e.message);
      }
    };
    void poll();
    const timer = setInterval(poll, 5000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [screen, selectedVisit?.id, selectedVisit?.status]);
  async function assess() {
    setBusy(true);
    setError("");
    try {
      const r = await api<{ specialties: string[] }>("/api/guidance", "POST", {
        text: symptoms.trim(),
      });
      setSuggestions(r.specialties);
      go("guidance");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function selectDoctor(d: Provider) {
    setDoctor(d);
    setSlots([]);
    setSlot("");
    setSlotsLoading(true);
    bookingKey.current = newRequestId();
    go("doctor");
    try {
      setSlots(
        (await api<{ slots: Slot[] }>(`/api/providers/${d.id}/slots`)).slots,
      );
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSlotsLoading(false);
    }
  }
  async function book() {
    if (!doctor || !slot) return;
    setBusy(true);
    setError("");
    try {
      const a = await api<Appointment>("/api/appointments", "POST", {
        provider_id: doctor.id,
        slot,
        request_id: bookingKey.current,
      });
      setConfirmed(a);
      setActiveId(a.id);
      go("confirmed");
      await loadVisits();
    } catch (e: any) {
      setError(e.message);
      try {
        setSlots(
          (await api<{ slots: Slot[] }>(`/api/providers/${doctor.id}/slots`))
            .slots,
        );
      } catch {}
    } finally {
      setBusy(false);
    }
  }
  async function checkIn(a: Appointment) {
    setBusy(true);
    setError("");
    try {
      await api(`/api/appointments/${a.id}/check-in`, "POST");
      setActiveId(a.id);
      await loadVisits();
      go("queue");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function cancel(a: Appointment) {
    setBusy(true);
    setError("");
    try {
      await api(`/api/appointments/${a.id}/cancel`, "POST");
      setCancelId(null);
      await loadVisits();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function advance() {
    if (!selectedVisit) return;
    setBusy(true);
    try {
      setQueue(
        await api<Queue>(
          `/api/appointments/${selectedVisit.id}/demo-advance`,
          "POST",
        ),
      );
      await loadVisits();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const browse = (specialty = "All") => {
    setFilter(specialty);
    setQuery("");
    go("doctors");
  };
  function doctorCard(d: Provider) {
    return (
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`View ${d.name}`}
        onPress={() => void selectDoctor(d)}
        key={d.id}
        style={[
          s.card,
          s.doctorCard,
          wide && screen === "doctors" && { width: "48.8%" },
        ]}
      >
        <View style={[s.avatar, { backgroundColor: d.color }]}>
          <Text style={s.initials}>{d.initials}</Text>
        </View>
        <View style={{ flex: 1, gap: 5 }}>
          <Text style={s.h3}>{d.name}</Text>
          <Text style={s.green}>{d.specialty}</Text>
          <Text style={s.small}>{d.hospital}</Text>
          <Text style={s.small}>{d.area} · Demo provider</Text>
        </View>
        <ChevronRight size={19} color={C.green} />
      </Pressable>
    );
  }
  function visitCard(a: Appointment) {
    return (
      <View style={[s.card, { gap: 15 }]} key={a.id}>
        <View style={s.between}>
          <Text style={s.tag}>{status(a.status)}</Text>
          <Text style={s.small}>{a.token}</Text>
        </View>
        <Text style={s.h3}>{a.provider.name}</Text>
        <Text style={s.body}>
          {a.provider.specialty} · {a.provider.hospital}
        </Text>
        <View style={s.row}>
          <CalendarDays size={17} color={C.green} />
          <Text style={s.body}>
            {date(a.slot)} · {time(a.slot)} IST
          </Text>
        </View>
        {a.status === "booked" && (
          <>
            <Button
              title="Check in to demo queue"
              busy={busy}
              onPress={() => void checkIn(a)}
            />
            {cancelId === a.id ? (
              <View style={{ gap: 10 }}>
                <Text style={s.body}>Cancel this demo appointment?</Text>
                <Button
                  title="Yes, cancel visit"
                  secondary
                  busy={busy}
                  onPress={() => void cancel(a)}
                />
                <Pressable
                  accessibilityRole="button"
                  onPress={() => setCancelId(null)}
                >
                  <Text style={s.link}>Keep appointment</Text>
                </Pressable>
              </View>
            ) : (
              <Pressable
                accessibilityRole="button"
                onPress={() => setCancelId(a.id)}
              >
                <Text style={s.link}>Cancel appointment</Text>
              </Pressable>
            )}
          </>
        )}
        {["checked_in", "ready"].includes(a.status) && (
          <Button
            title="View live queue"
            onPress={() => {
              setActiveId(a.id);
              go("queue");
            }}
          />
        )}
      </View>
    );
  }
  const tab = ["doctor", "doctors", "guidance", "symptoms"].includes(screen)
    ? "doctors"
    : screen === "confirmed"
      ? "appointments"
      : screen;
  return (
    <View style={s.root}>
      <StatusBar style="dark" />
      <View style={s.demoBar}>
        <Text style={s.demoBarText}>
          PROJECT DEMO · Fictional doctors & bookings
        </Text>
      </View>
      <View style={s.header}>
        <View style={[s.headerInner, { maxWidth: wide ? 1120 : 590 }]}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Carelane home"
            onPress={() => go("home")}
            style={s.row}
          >
            <View style={s.logo}>
              <Plus color="#fff" size={23} strokeWidth={3} />
            </View>
            <Text style={s.wordmark}>
              carelane<Text style={{ color: C.green }}>.</Text>
            </Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="About demo profile"
            onPress={() => go("about")}
            style={s.profile}
          >
            <UserRound size={21} color={C.green} />
          </Pressable>
        </View>
      </View>
      <ScrollView
        ref={scroll}
        style={{ flex: 1 }}
        contentContainerStyle={[s.content, { maxWidth: wide ? 1120 : 590 }]}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              setError("");
              void load();
            }}
          />
        }
        keyboardShouldPersistTaps="handled"
      >
        {!["home", "doctors", "appointments", "queue"].includes(screen) && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Go back"
            onPress={back}
            style={s.back}
          >
            <ArrowLeft size={19} color={C.green} />
            <Text style={s.green}>Back</Text>
          </Pressable>
        )}
        {!!error && (
          <View style={s.error} accessibilityRole="alert">
            <Text style={{ flex: 1, color: "#963F33", lineHeight: 21 }}>
              {error}
            </Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Dismiss error"
              onPress={() => setError("")}
            >
              <X size={18} color="#963F33" />
            </Pressable>
          </View>
        )}
        {loading ? (
          <View style={s.empty}>
            <ActivityIndicator color={C.green} />
            <Text style={s.body}>Getting your care space ready…</Text>
          </View>
        ) : (
          <>
            {screen === "home" && (
              <>
                <View style={s.between}>
                  <Text style={s.eyebrow}>YOUR HEALTH, A LITTLE SIMPLER</Text>
                  <View style={s.row}>
                    <MapPin size={14} color={C.muted} />
                    <Text style={s.small}>Patiala</Text>
                  </View>
                </View>
                <Text style={[s.h1, wide && { fontSize: 39 }]}>
                  Hello, Demo Patient{" "}
                  <Text style={{ color: "#D6A253" }}>✦</Text>
                </Text>
                <Text style={s.subtitle}>
                  A clearer path from feeling unwell to finding care.
                </Text>
                <View style={[s.grid, wide && { flexDirection: "row" }]}>
                  <View style={[s.hero, { flex: wide ? 1.35 : undefined }]}>
                    <View style={s.heroTop}>
                      <View style={s.heroIcon}>
                        <HeartPulse size={31} color={C.green} />
                      </View>
                      <Text style={s.pill}>AI SPECIALTY GUIDE</Text>
                    </View>
                    <Text style={s.heroTitle}>
                      Not sure where{"\n"}to start?
                    </Text>
                    <Text style={[s.body, { maxWidth: 350, marginBottom: 22 }]}>
                      Describe how you’re feeling. Explore a department to
                      discuss with clinic staff.
                    </Text>
                    <Button
                      title="Start symptom guide"
                      onPress={() => go("symptoms")}
                    />
                    <Text style={s.heroFoot}>
                      Experimental guidance · No diagnosis
                    </Text>
                  </View>
                  <View
                    style={[
                      s.card,
                      {
                        flex: wide ? 1 : undefined,
                        gap: 16,
                        justifyContent: "space-between",
                      },
                    ]}
                  >
                    <View style={s.between}>
                      <Text style={s.h3}>Your next visit</Text>
                      <CalendarDays color={C.green} size={22} />
                    </View>
                    {current ? (
                      <>
                        <View>
                          <Text style={s.h2}>{current.provider.name}</Text>
                          <Text style={s.body}>
                            {current.provider.specialty}
                          </Text>
                        </View>
                        <Text style={s.body}>
                          {date(current.slot)} · {time(current.slot)} IST
                        </Text>
                        <Button
                          title="Manage appointment"
                          secondary
                          onPress={() => go("appointments")}
                        />
                      </>
                    ) : (
                      <>
                        <View style={s.emptySmall}>
                          <View style={s.calendarArt}>
                            <CalendarDays size={37} color={C.green} />
                          </View>
                          <Text style={s.h3}>Make room for your health</Text>
                          <Text style={[s.body, { textAlign: "center" }]}>
                            Your upcoming appointment will appear here.
                          </Text>
                        </View>
                        <Button
                          title="Find a doctor"
                          secondary
                          onPress={() => browse()}
                        />
                      </>
                    )}
                  </View>
                </View>
                <View style={s.sectionHeading}>
                  <Text style={s.h2}>Care, one step at a time</Text>
                  <Text style={s.small}>A simple visit journey</Text>
                </View>
                <View style={[s.steps, wide && { flexDirection: "row" }]}>
                  {[
                    [
                      "01",
                      "Find your direction",
                      "Explore departments with the symptom guide.",
                    ],
                    [
                      "02",
                      "Choose your visit",
                      "Pick a demo doctor and an available time.",
                    ],
                    [
                      "03",
                      "Skip the guesswork",
                      "Check in and follow your simulated queue.",
                    ],
                  ].map(([n, title, desc]) => (
                    <View style={s.step} key={n}>
                      <Text style={s.stepNumber}>{n}</Text>
                      <View style={{ flex: 1, gap: 6 }}>
                        <Text style={s.h3}>{title}</Text>
                        <Text style={s.small}>{desc}</Text>
                      </View>
                    </View>
                  ))}
                </View>
                <View style={s.sectionHeading}>
                  <Text style={s.h2}>Explore specialists</Text>
                  <Pressable
                    accessibilityRole="button"
                    onPress={() => browse()}
                  >
                    <Text style={s.link}>View all →</Text>
                  </Pressable>
                </View>
                <View style={{ gap: 12 }}>
                  {doctors.slice(0, 3).map(doctorCard)}
                </View>
                {!doctors.length && (
                  <Button
                    title="Retry connection"
                    secondary
                    onPress={() => void load()}
                  />
                )}
              </>
            )}
            {screen === "symptoms" && (
              <>
                <Text style={s.eyebrow}>LET’S FIND A STARTING POINT</Text>
                <Text style={s.h1}>How are you feeling?</Text>
                <Text style={s.subtitle}>
                  Use an example symptom description for this project demo.
                </Text>
                <View style={[s.card, { gap: 18 }]}>
                  <Text style={s.h3}>Describe the symptoms</Text>
                  <TextInput
                    accessibilityLabel="Describe the symptoms"
                    placeholder="For example: an itchy rash with red patches on my arms for two days…"
                    placeholderTextColor={C.muted}
                    multiline
                    maxLength={2000}
                    value={symptoms}
                    onChangeText={setSymptoms}
                    style={s.textarea}
                    textAlignVertical="top"
                  />
                  <View style={s.between}>
                    <Text style={s.small}>
                      Please leave out names and personal details.
                    </Text>
                    <Text style={s.small}>{symptoms.length}/2000</Text>
                  </View>
                  <Text style={s.eyebrow}>OR TRY AN EXAMPLE</Text>
                  <View style={s.wrap}>
                    {[
                      [
                        "Itchy skin",
                        "An itchy skin rash with red patches on my arms for two days.",
                      ],
                      [
                        "Cough & fever",
                        "I have a persistent cough and a fever with chest discomfort.",
                      ],
                      [
                        "Neck pain",
                        "My neck feels stiff and painful when I turn my head.",
                      ],
                    ].map(([title, value]) => (
                      <Pressable
                        accessibilityRole="button"
                        key={title}
                        onPress={() => setSymptoms(value)}
                        style={s.chip}
                      >
                        <Text style={s.green}>{title}</Text>
                      </Pressable>
                    ))}
                  </View>
                  <Button
                    title="Explore suggested departments"
                    busy={busy}
                    disabled={symptoms.trim().length < 10}
                    onPress={() => void assess()}
                  />
                </View>
                <Note text="Experimental model suggestions need clinic staff confirmation. This guide does not diagnose conditions or assess urgency. If you think this may be an emergency, seek urgent medical help." />
              </>
            )}
            {screen === "guidance" && (
              <>
                <View style={s.featureIcon}>
                  <Sparkles size={30} color={C.green} />
                </View>
                <Text style={s.h1}>A starting point for care</Text>
                <Text style={s.subtitle}>
                  Our model suggested these departments to explore.
                </Text>
                <Note text="Confirm the right department with clinic staff before a real appointment. These suggestions are experimental and may be incorrect." />
                <View style={{ gap: 12 }}>
                  {suggestions.map((item, i) => (
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel={`Explore ${item}`}
                      onPress={() => browse(item)}
                      style={[s.card, s.between]}
                      key={item}
                    >
                      <View style={s.row}>
                        <View style={s.rank}>
                          <Text style={s.green}>{i + 1}</Text>
                        </View>
                        <View style={{ flexShrink: 1 }}>
                          <Text style={s.h3}>{item}</Text>
                          <Text style={s.small}>Explore demo doctors</Text>
                        </View>
                      </View>
                      <ChevronRight size={20} color={C.green} />
                    </Pressable>
                  ))}
                </View>
                <Button
                  title="Browse all doctors"
                  secondary
                  onPress={() => browse()}
                />
              </>
            )}
            {screen === "doctors" && (
              <>
                <Text style={s.eyebrow}>FIND YOUR CARE TEAM</Text>
                <Text style={s.h1}>A doctor for your next step.</Text>
                <Text style={s.subtitle}>
                  Explore fictional specialists in our Patiala demo directory.
                </Text>
                <View style={s.search}>
                  <Search size={20} color={C.muted} />
                  <TextInput
                    accessibilityLabel="Search doctors"
                    placeholder="Search doctor, department or clinic"
                    value={query}
                    onChangeText={setQuery}
                    style={s.searchInput}
                    placeholderTextColor={C.muted}
                  />
                </View>
                <ScrollView
                  horizontal
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={{ gap: 8, paddingVertical: 16 }}
                >
                  {["All", ...new Set(doctors.map((d) => d.specialty))].map(
                    (f) => (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityState={{ selected: filter === f }}
                        onPress={() => setFilter(f)}
                        style={[s.chip, filter === f && s.selectedChip]}
                        key={f}
                      >
                        <Text style={filter === f ? s.selectedText : s.green}>
                          {f}
                        </Text>
                      </Pressable>
                    ),
                  )}
                </ScrollView>
                <View style={[s.wrap, { gap: 16 }]}>
                  {doctors
                    .filter(
                      (d) =>
                        (filter === "All" || d.specialty === filter) &&
                        `${d.name} ${d.specialty} ${d.hospital}`
                          .toLowerCase()
                          .includes(query.toLowerCase()),
                    )
                    .map(doctorCard)}
                </View>
                {!doctors.some(
                  (d) =>
                    (filter === "All" || d.specialty === filter) &&
                    `${d.name} ${d.specialty} ${d.hospital}`
                      .toLowerCase()
                      .includes(query.toLowerCase()),
                ) && (
                  <View style={s.empty}>
                    <Text style={s.h3}>No doctors found</Text>
                    <Button
                      title="Clear filters"
                      secondary
                      onPress={() => {
                        setFilter("All");
                        setQuery("");
                      }}
                    />
                  </View>
                )}
              </>
            )}
            {screen === "doctor" && doctor && (
              <>
                <View style={[s.card, { alignItems: "center", gap: 12 }]}>
                  <View
                    style={[
                      s.avatar,
                      { backgroundColor: doctor.color, width: 82, height: 82 },
                    ]}
                  >
                    <Text style={[s.initials, { fontSize: 27 }]}>
                      {doctor.initials}
                    </Text>
                  </View>
                  <Text style={s.h2}>{doctor.name}</Text>
                  <Text style={s.green}>{doctor.specialty}</Text>
                  <Text style={s.body}>
                    {doctor.hospital} · {doctor.area}
                  </Text>
                  <Text style={s.tag}>Fictional demo provider</Text>
                </View>
                <View style={s.sectionHeading}>
                  <Text style={s.h2}>Choose a time</Text>
                  <Text style={s.small}>All times IST</Text>
                </View>
                {slotsLoading ? (
                  <ActivityIndicator color={C.green} />
                ) : (
                  <View style={[s.card, { gap: 20 }]}>
                    {[...new Set(slots.map((v) => v.value.slice(0, 10)))].map(
                      (day) => (
                        <View style={{ gap: 10 }} key={day}>
                          <Text style={s.h3}>
                            {date(day + "T12:00:00+05:30")}
                          </Text>
                          <View style={s.wrap}>
                            {slots
                              .filter((v) => v.value.startsWith(day))
                              .map((v) => (
                                <Pressable
                                  accessibilityRole="button"
                                  accessibilityLabel={`Book ${date(v.value)} ${time(v.value)}`}
                                  accessibilityState={{
                                    selected: slot === v.value,
                                    disabled: !v.available,
                                  }}
                                  disabled={!v.available}
                                  onPress={() => {
                                    setSlot(v.value);
                                    bookingKey.current = newRequestId();
                                  }}
                                  key={v.value}
                                  style={[
                                    s.chip,
                                    slot === v.value && s.selectedChip,
                                    !v.available && { opacity: 0.3 },
                                  ]}
                                >
                                  <Text
                                    style={
                                      slot === v.value
                                        ? s.selectedText
                                        : s.green
                                    }
                                  >
                                    {time(v.value)}
                                  </Text>
                                </Pressable>
                              ))}
                          </View>
                        </View>
                      ),
                    )}
                    {!slots.length && (
                      <Button
                        title="Reload available times"
                        secondary
                        onPress={() => void selectDoctor(doctor)}
                      />
                    )}
                  </View>
                )}
                <View style={[s.card, { gap: 16 }]}>
                  <View style={s.between}>
                    <Text style={s.body}>Illustrative consultation fee</Text>
                    <Text style={s.h2}>₹{doctor.fee}</Text>
                  </View>
                  <Text style={s.small}>
                    Demo booking only. No payment is taken and no clinic is
                    contacted.
                  </Text>
                  <Button
                    title="Confirm demo appointment"
                    disabled={
                      !slot ||
                      !slots.some((v) => v.value === slot && v.available)
                    }
                    busy={busy}
                    onPress={() => void book()}
                  />
                </View>
              </>
            )}
            {screen === "confirmed" && confirmed && (
              <>
                <View style={s.successIcon}>
                  <Check size={36} color={C.green} />
                </View>
                <Text style={[s.h1, { textAlign: "center" }]}>
                  You’re all set.
                </Text>
                <Text style={[s.subtitle, { textAlign: "center" }]}>
                  Your demo appointment is saved.
                </Text>
                <View style={[s.card, { alignItems: "center", gap: 17 }]}>
                  <Text style={s.eyebrow}>YOUR VISIT TOKEN</Text>
                  <Text style={s.token}>{confirmed.token}</Text>
                  <View style={s.divider} />
                  <Text style={s.h2}>{confirmed.provider.name}</Text>
                  <Text style={s.body}>{confirmed.provider.specialty}</Text>
                  <Text style={s.body}>
                    {date(confirmed.slot)} · {time(confirmed.slot)} IST
                  </Text>
                  <Text style={s.small}>{confirmed.provider.hospital}</Text>
                </View>
                <Button
                  title="See my appointments"
                  onPress={() => go("appointments")}
                />
                <Note text="For this demo, you can check in immediately and use the demo desk to move the queue forward." />
              </>
            )}
            {screen === "appointments" && (
              <>
                <Text style={s.eyebrow}>YOUR CARE, ORGANIZED</Text>
                <Text style={s.h1}>My visits</Text>
                <Text style={s.subtitle}>
                  Your demo appointments are saved on this device’s session.
                </Text>
                {visits.length ? (
                  <View style={{ gap: 16 }}>{visits.map(visitCard)}</View>
                ) : (
                  <View style={[s.card, s.empty]}>
                    <CalendarDays size={40} color={C.green} />
                    <Text style={s.h2}>Your first visit starts here</Text>
                    <Text style={s.body}>
                      Choose a doctor and a time that works for you.
                    </Text>
                    <Button title="Find a doctor" onPress={() => browse()} />
                  </View>
                )}
              </>
            )}
            {screen === "queue" && (
              <>
                <View style={s.between}>
                  <Text style={s.eyebrow}>
                    A LITTLE LESS WAITING, A LITTLE MORE CLARITY
                  </Text>
                </View>
                <Text style={s.h1}>Your live queue</Text>
                <Text style={s.subtitle}>
                  A simulated queue for your demo visit.
                </Text>
                {!selectedVisit ? (
                  <View style={[s.card, s.empty]}>
                    <Ticket size={42} color={C.green} />
                    <Text style={s.h2}>No active visit yet</Text>
                    <Text style={s.body}>
                      Book a demo appointment to try the queue.
                    </Text>
                    <Button title="Find a doctor" onPress={() => browse()} />
                  </View>
                ) : selectedVisit.status === "booked" ? (
                  visitCard(selectedVisit)
                ) : queue ? (
                  <>
                    <View style={[s.queueHero, { gap: 16 }]}>
                      <Text style={s.pill}>
                        {queue.appointment.status === "completed"
                          ? "VISIT COMPLETE"
                          : queue.ahead === 0
                            ? "YOUR TURN"
                            : "YOU’RE CHECKED IN"}
                      </Text>
                      <Text style={s.small}>Your token</Text>
                      <Text style={s.token}>{queue.appointment.token}</Text>
                      <View
                        style={[
                          s.row,
                          { width: "100%", justifyContent: "space-evenly" },
                        ]}
                      >
                        <View style={s.stat}>
                          <Text style={s.statValue}>{queue.ahead}</Text>
                          <Text style={s.small}>people ahead</Text>
                        </View>
                        <View style={s.stat}>
                          <Text style={s.statValue}>
                            {queue.estimated_minutes}
                            <Text style={{ fontSize: 17 }}> min</Text>
                          </Text>
                          <Text style={s.small}>simulated estimate</Text>
                        </View>
                      </View>
                      <View style={s.progress}>
                        {[0, 1, 2, 3].map((i) => (
                          <View
                            key={i}
                            style={[
                              s.progressPart,
                              i <= 3 - queue.ahead && {
                                backgroundColor: C.green,
                              },
                            ]}
                          />
                        ))}
                      </View>
                      <Text style={[s.body, { textAlign: "center" }]}>
                        {queue.appointment.status === "completed"
                          ? "Thanks for trying the visit journey."
                          : queue.ahead === 0
                            ? "The demo desk is ready for you."
                            : "We’ll keep this screen up to date as the demo queue moves."}
                      </Text>
                    </View>
                    <View style={[s.card, { gap: 10 }]}>
                      <Text style={s.h3}>
                        {queue.appointment.provider.name}
                      </Text>
                      <Text style={s.body}>
                        {queue.appointment.provider.hospital}
                      </Text>
                      <Text style={s.small}>
                        Demo updates every 5 seconds · Not a real waiting time
                      </Text>
                    </View>
                    {queue.appointment.status !== "completed" && (
                      <>
                        <Pressable
                          accessibilityRole="button"
                          onPress={() => setDesk(!desk)}
                          style={s.back}
                        >
                          <Info size={17} color={C.green} />
                          <Text style={s.link}>
                            {desk ? "Close demo desk" : "Open demo desk"}
                          </Text>
                        </Pressable>
                        {desk && (
                          <View style={[s.card, { gap: 14 }]}>
                            <Text style={s.h3}>Try the queue in action</Text>
                            <Text style={s.body}>
                              Move one fictional patient through the queue.
                              Nothing changes at a real clinic.
                            </Text>
                            <Button
                              title={
                                queue.ahead
                                  ? "Call next demo patient"
                                  : "Complete demo visit"
                              }
                              busy={busy}
                              onPress={() => void advance()}
                            />
                          </View>
                        )}
                      </>
                    )}
                  </>
                ) : (
                  <ActivityIndicator color={C.green} />
                )}
              </>
            )}
            {screen === "about" && (
              <>
                <Text style={s.h1}>Your demo space</Text>
                <Text style={s.subtitle}>
                  A first look at the Carelane patient experience.
                </Text>
                <View style={[s.card, { gap: 18 }]}>
                  <UserRound size={35} color={C.green} />
                  <Text style={s.h2}>Demo Patient</Text>
                  <Text style={s.body}>
                    This anonymous session keeps your demo visits between
                    reloads. Clearing app storage starts a new session.
                  </Text>
                  <View style={s.divider} />
                  <Text style={s.h3}>Built for the project</Text>
                  <Text style={s.body}>
                    Specialty guidance uses our trained text model. Waiting
                    estimates use simulated data. Doctors, clinics, fees and
                    appointments are fictional.
                  </Text>
                  <Text style={s.body}>
                    Symptom text is processed by the local model service and is
                    not saved in the booking database. Please use example
                    symptoms and avoid real personal information.
                  </Text>
                  <Text style={s.small}>
                    Version 0.1 · Patient app prototype
                  </Text>
                </View>
              </>
            )}
          </>
        )}
        <View style={s.footer}>
          <Plus size={12} color={C.muted} />
          <Text style={s.small}>Made for a calmer care journey.</Text>
        </View>
      </ScrollView>
      <View style={s.navOuter}>
        <View style={[s.nav, { maxWidth: wide ? 750 : 590 }]}>
          {(
            [
              { id: "home", label: "Home", Icon: Home },
              { id: "doctors", label: "Find care", Icon: Stethoscope },
              { id: "appointments", label: "My visits", Icon: CalendarDays },
              { id: "queue", label: "Live queue", Icon: Ticket },
            ] as const
          ).map(({ id, label, Icon }) => (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={label}
              accessibilityState={{ selected: tab === id }}
              key={id}
              onPress={() => go(id)}
              style={s.navItem}
            >
              <View
                style={[s.navIcon, tab === id && { backgroundColor: C.mint }]}
              >
                <Icon size={22} color={tab === id ? C.green : C.muted} />
              </View>
              <Text
                style={[
                  s.navLabel,
                  tab === id && { color: C.green, fontWeight: "700" },
                ]}
              >
                {label}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  demoBar: { backgroundColor: "#DFECE5", alignItems: "center", padding: 7 },
  demoBarText: {
    color: "#57716A",
    fontSize: 10,
    letterSpacing: 1.1,
    fontWeight: "600",
  },
  header: {
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderColor: C.line,
  },
  headerInner: {
    alignSelf: "center",
    width: "100%",
    paddingHorizontal: 24,
    height: 77,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  logo: {
    backgroundColor: C.green,
    borderRadius: 11,
    width: 33,
    height: 33,
    alignItems: "center",
    justifyContent: "center",
  },
  wordmark: {
    fontSize: 28,
    letterSpacing: -1.4,
    fontWeight: "700",
    color: C.ink,
  },
  profile: {
    width: 41,
    height: 41,
    borderRadius: 21,
    backgroundColor: C.mint,
    alignItems: "center",
    justifyContent: "center",
  },
  content: {
    width: "100%",
    alignSelf: "center",
    padding: 24,
    paddingTop: 30,
    gap: 17,
  },
  row: { flexDirection: "row", alignItems: "center", gap: 9 },
  between: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
  },
  wrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  grid: { gap: 20, marginTop: 10 },
  eyebrow: {
    fontSize: 10,
    fontWeight: "700",
    color: C.muted,
    letterSpacing: 1.4,
    flexShrink: 1,
  },
  h1: {
    fontSize: 30,
    color: C.ink,
    fontWeight: "700",
    letterSpacing: -1.1,
    lineHeight: 43,
  },
  h2: { fontSize: 21, fontWeight: "600", color: C.ink, letterSpacing: -0.5 },
  h3: { fontSize: 16, fontWeight: "600", color: C.ink },
  subtitle: {
    fontSize: 15,
    color: C.muted,
    lineHeight: 24,
    marginTop: -9,
    marginBottom: 8,
  },
  body: { color: "#5E7771", fontSize: 14, lineHeight: 23 },
  small: { color: C.muted, fontSize: 12, lineHeight: 19 },
  green: { color: C.green, fontSize: 13, fontWeight: "500" },
  card: {
    backgroundColor: "#FFF",
    borderColor: C.line,
    borderWidth: 1,
    borderRadius: 21,
    padding: 22,
  },
  hero: {
    backgroundColor: "#E4F0E9",
    borderRadius: 24,
    padding: 27,
    overflow: "hidden",
  },
  heroTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 22,
    gap: 8,
  },
  heroIcon: { backgroundColor: "#F7FCF8", padding: 12, borderRadius: 18 },
  pill: {
    backgroundColor: "#F5FBF7",
    color: C.green,
    fontSize: 10,
    letterSpacing: 1,
    fontWeight: "700",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    overflow: "hidden",
  },
  heroTitle: {
    fontSize: 34,
    lineHeight: 40,
    color: C.ink,
    letterSpacing: -1,
    fontWeight: "600",
    marginBottom: 13,
  },
  heroFoot: {
    color: "#68877B",
    fontSize: 11,
    textAlign: "center",
    marginTop: 13,
  },
  button: {
    backgroundColor: C.green,
    paddingHorizontal: 20,
    minHeight: 49,
    paddingVertical: 13,
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  buttonText: { color: "#FFF", fontWeight: "600", fontSize: 14, flexShrink: 1 },
  secondary: {
    backgroundColor: C.mint,
    borderColor: "#DCEAE2",
    borderWidth: 1,
  },
  link: { color: C.green, fontSize: 13, fontWeight: "600", paddingVertical: 5 },
  empty: {
    alignItems: "center",
    justifyContent: "center",
    gap: 20,
    paddingVertical: 40,
  },
  emptySmall: { alignItems: "center", gap: 12, paddingVertical: 10 },
  calendarArt: {
    width: 73,
    height: 73,
    borderRadius: 24,
    backgroundColor: "#F1F6F0",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 7,
  },
  sectionHeading: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 15,
    gap: 10,
  },
  steps: { backgroundColor: "#EFF3ED", borderRadius: 18, padding: 21, gap: 25 },
  step: { flex: 1, flexDirection: "row", gap: 14 },
  stepNumber: { fontSize: 22, color: "#8CAC9C", fontWeight: "400" },
  doctorCard: {
    flexDirection: "row",
    gap: 16,
    alignItems: "center",
    width: "100%",
  },
  avatar: {
    width: 56,
    height: 62,
    borderRadius: 17,
    alignItems: "center",
    justifyContent: "center",
  },
  initials: { color: "#5D7B75", fontSize: 18, fontWeight: "500" },
  tag: {
    fontSize: 11,
    color: C.green,
    backgroundColor: C.mint,
    alignSelf: "flex-start",
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 6,
  },
  note: {
    flexDirection: "row",
    gap: 10,
    padding: 17,
    backgroundColor: "#EBF1EB",
    borderRadius: 13,
  },
  noteText: { flex: 1, color: "#637B72", fontSize: 12, lineHeight: 20 },
  textarea: {
    minHeight: 150,
    borderWidth: 1,
    borderColor: C.line,
    backgroundColor: "#FAFCF9",
    borderRadius: 13,
    padding: 15,
    fontSize: 15,
    lineHeight: 24,
    color: C.ink,
  },
  chip: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: C.line,
    backgroundColor: "#FFF",
  },
  selectedChip: { backgroundColor: C.green, borderColor: C.green },
  selectedText: { color: "#FFF", fontSize: 13, fontWeight: "600" },
  search: {
    flexDirection: "row",
    gap: 12,
    borderWidth: 1,
    borderColor: C.line,
    borderRadius: 13,
    backgroundColor: "#FFF",
    alignItems: "center",
    paddingHorizontal: 16,
  },
  searchInput: { minHeight: 51, flex: 1, color: C.ink, fontSize: 14 },
  featureIcon: {
    backgroundColor: C.mint,
    borderRadius: 18,
    padding: 17,
    alignSelf: "flex-start",
  },
  rank: {
    backgroundColor: C.mint,
    borderRadius: 12,
    height: 37,
    width: 37,
    alignItems: "center",
    justifyContent: "center",
  },
  back: {
    flexDirection: "row",
    gap: 8,
    alignItems: "center",
    paddingVertical: 5,
  },
  error: {
    flexDirection: "row",
    gap: 12,
    backgroundColor: "#FCEDE7",
    padding: 16,
    borderRadius: 12,
  },
  successIcon: {
    backgroundColor: "#DCEEE4",
    width: 78,
    height: 78,
    borderRadius: 39,
    alignSelf: "center",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 15,
  },
  token: { color: C.ink, fontSize: 42, letterSpacing: 3, fontWeight: "600" },
  divider: { height: 1, backgroundColor: C.line, width: "100%" },
  queueHero: {
    backgroundColor: "#E3F0E8",
    borderRadius: 25,
    padding: 28,
    alignItems: "center",
  },
  stat: { alignItems: "center", gap: 5 },
  statValue: { color: C.ink, fontSize: 35, fontWeight: "600" },
  progress: { flexDirection: "row", gap: 5, width: "100%", marginTop: 5 },
  progressPart: {
    height: 5,
    flex: 1,
    borderRadius: 5,
    backgroundColor: "#C8DDD1",
  },
  footer: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 6,
    paddingVertical: 24,
  },
  navOuter: {
    backgroundColor: "#FFF",
    borderTopWidth: 1,
    borderColor: C.line,
    paddingBottom: Platform.OS === "ios" ? 23 : 9,
  },
  nav: {
    width: "100%",
    alignSelf: "center",
    flexDirection: "row",
    paddingTop: 8,
  },
  navItem: { flex: 1, alignItems: "center", gap: 3 },
  navIcon: { paddingHorizontal: 19, paddingVertical: 7, borderRadius: 17 },
  navLabel: { fontSize: 10, color: C.muted },
});
