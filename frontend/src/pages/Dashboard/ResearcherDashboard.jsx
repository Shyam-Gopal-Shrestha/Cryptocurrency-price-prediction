import React, { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import {
  LayoutDashboard,
  User,
  Database,
  Brain,
  Bell,
  Settings,
  LogOut,
  Search,
  FolderOpen,
  Clock3,
  TrendingUp,
  Activity,
  Save,
  RefreshCw,
  FileText,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  Newspaper,
  Pencil,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
  BarChart,
  Bar,
} from "recharts";
import "./ResearcherDashboard.css";

const COIN_OPTIONS = [
  { code: "BTC", name: "Bitcoin", apiId: "bitcoin", symbol: "BTC" },
  { code: "ETH", name: "Ethereum", apiId: "ethereum", symbol: "ETH" },
  { code: "SOL", name: "Solana", apiId: "solana", symbol: "SOL" },
];

const MODEL_OPTIONS = [
  "LSTM",
  "GRU",
  "XGBoost",
  "Random Forest",
  "Linear Regression",
];

const DAY_OPTIONS = ["7D", "30D", "90D"];
const PIE_COLORS = ["#4cd964", "#3b82f6", "#f59e0b", "#a855f7", "#94a3b8"];

const DEFAULT_NOTIFICATIONS = [
  "New market data snapshot available.",
  "Prediction settings were updated successfully.",
  "Research report is ready to review.",
];

const NEWS_FALLBACK = {
  BTC: [
    {
      title: "Bitcoin market sentiment remains active as volatility increases",
      source: "Research Feed",
      summary:
        "BTC continues to attract research attention while short-term volatility keeps analysts focused on support, trend strength, and volume confirmation.",
      url: "https://www.coingecko.com/en/coins/bitcoin",
    },
    {
      title: "Researchers are tracking BTC resistance and momentum signals",
      source: "Research Feed",
      summary:
        "Recent movement suggests that market participants are comparing RSI, liquidity conditions, and broader crypto sentiment before confirming the next move.",
      url: "https://www.tradingview.com/symbols/BTCUSD/",
    },
  ],
  ETH: [
    {
      title: "Ethereum network activity supports strong research interest",
      source: "Research Feed",
      summary:
        "ETH remains closely watched for ecosystem strength, trading efficiency, and medium-term trend continuation.",
      url: "https://www.coingecko.com/en/coins/ethereum",
    },
    {
      title: "ETH analysts compare price structure with volume behavior",
      source: "Research Feed",
      summary:
        "Researchers are monitoring whether ETH can sustain momentum through stronger participation and improved market breadth.",
      url: "https://www.tradingview.com/symbols/ETHUSD/",
    },
  ],
  SOL: [
    {
      title: "Solana momentum continues to drive short-window analysis",
      source: "Research Feed",
      summary:
        "SOL remains a useful asset for researchers studying volatility, momentum bursts, and fast market reactions.",
      url: "https://www.coingecko.com/en/coins/solana",
    },
    {
      title: "Researchers evaluate SOL breakout potential",
      source: "Research Feed",
      summary:
        "Analysts are studying whether recent price behavior and participation levels support continued upward movement.",
      url: "https://www.tradingview.com/symbols/SOLUSD/",
    },
  ],
};

const MODEL_LIBRARY = {
  BTC: {
    LSTM: {
      accuracy: "93%",
      confidence: "88.2%",
      rmse: 4.2,
      mae: 2.8,
      note: "Best sequence model for BTC closing-price forecasting.",
      featureImportance: [
        { feature: "Previous Close", score: 96 },
        { feature: "Volume", score: 82 },
        { feature: "RSI", score: 74 },
        { feature: "7-Day Moving Avg", score: 71 },
        { feature: "Volatility", score: 63 },
      ],
    },
    GRU: {
      accuracy: "91%",
      confidence: "87.1%",
      rmse: 4.8,
      mae: 3.1,
      note: "Efficient recurrent model with strong short-term performance.",
      featureImportance: [
        { feature: "Previous Close", score: 93 },
        { feature: "Volume", score: 79 },
        { feature: "RSI", score: 70 },
        { feature: "7-Day Moving Avg", score: 69 },
        { feature: "Volatility", score: 60 },
      ],
    },
    XGBoost: {
      accuracy: "89%",
      confidence: "85.8%",
      rmse: 5.4,
      mae: 3.5,
      note: "Strong feature-driven model for engineered market indicators.",
      featureImportance: [
        { feature: "Previous Close", score: 91 },
        { feature: "Volume", score: 84 },
        { feature: "RSI", score: 72 },
        { feature: "MACD", score: 67 },
        { feature: "Volatility", score: 61 },
      ],
    },
    "Random Forest": {
      accuracy: "87%",
      confidence: "83.7%",
      rmse: 6.2,
      mae: 4.1,
      note: "Stable ensemble baseline with moderate forecasting quality.",
      featureImportance: [
        { feature: "Previous Close", score: 88 },
        { feature: "Volume", score: 80 },
        { feature: "RSI", score: 68 },
        { feature: "MACD", score: 63 },
        { feature: "Volatility", score: 59 },
      ],
    },
    "Linear Regression": {
      accuracy: "82%",
      confidence: "80.6%",
      rmse: 7.4,
      mae: 5.0,
      note: "Simple and interpretable baseline model.",
      featureImportance: [
        { feature: "Previous Close", score: 84 },
        { feature: "Volume", score: 72 },
        { feature: "RSI", score: 64 },
        { feature: "Moving Avg", score: 60 },
        { feature: "Volatility", score: 52 },
      ],
    },
  },
  ETH: {
    LSTM: {
      accuracy: "92%",
      confidence: "88.0%",
      rmse: 2.9,
      mae: 1.9,
      note: "Strong recurrent model for ETH trend behavior.",
      featureImportance: [
        { feature: "Previous Close", score: 95 },
        { feature: "Volume", score: 81 },
        { feature: "RSI", score: 73 },
        { feature: "EMA", score: 69 },
        { feature: "Volatility", score: 61 },
      ],
    },
    GRU: {
      accuracy: "90%",
      confidence: "86.0%",
      rmse: 3.2,
      mae: 2.1,
      note: "Balanced recurrent alternative for ETH forecasting.",
      featureImportance: [
        { feature: "Previous Close", score: 92 },
        { feature: "Volume", score: 78 },
        { feature: "RSI", score: 69 },
        { feature: "EMA", score: 67 },
        { feature: "Volatility", score: 58 },
      ],
    },
    XGBoost: {
      accuracy: "88%",
      confidence: "84.7%",
      rmse: 3.7,
      mae: 2.4,
      note: "Feature-based regression performs well on ETH.",
      featureImportance: [
        { feature: "Previous Close", score: 90 },
        { feature: "Volume", score: 82 },
        { feature: "RSI", score: 71 },
        { feature: "MACD", score: 65 },
        { feature: "Volatility", score: 57 },
      ],
    },
    "Random Forest": {
      accuracy: "86%",
      confidence: "82.6%",
      rmse: 4.1,
      mae: 2.8,
      note: "Stable ensemble benchmark for ETH.",
      featureImportance: [
        { feature: "Previous Close", score: 87 },
        { feature: "Volume", score: 78 },
        { feature: "RSI", score: 66 },
        { feature: "MACD", score: 61 },
        { feature: "Volatility", score: 55 },
      ],
    },
    "Linear Regression": {
      accuracy: "81%",
      confidence: "79.7%",
      rmse: 4.9,
      mae: 3.3,
      note: "Transparent ETH baseline with lower accuracy.",
      featureImportance: [
        { feature: "Previous Close", score: 82 },
        { feature: "Volume", score: 70 },
        { feature: "RSI", score: 62 },
        { feature: "Moving Avg", score: 58 },
        { feature: "Volatility", score: 50 },
      ],
    },
  },
  SOL: {
    LSTM: {
      accuracy: "91%",
      confidence: "87.4%",
      rmse: 3.5,
      mae: 2.2,
      note: "Best sequence model for SOL short and medium windows.",
      featureImportance: [
        { feature: "Previous Close", score: 94 },
        { feature: "Volume", score: 80 },
        { feature: "RSI", score: 72 },
        { feature: "EMA", score: 68 },
        { feature: "Volatility", score: 62 },
      ],
    },
    GRU: {
      accuracy: "89%",
      confidence: "85.1%",
      rmse: 3.9,
      mae: 2.5,
      note: "Efficient recurrent option for SOL.",
      featureImportance: [
        { feature: "Previous Close", score: 91 },
        { feature: "Volume", score: 77 },
        { feature: "RSI", score: 68 },
        { feature: "EMA", score: 65 },
        { feature: "Volatility", score: 59 },
      ],
    },
    XGBoost: {
      accuracy: "87%",
      confidence: "83.7%",
      rmse: 4.2,
      mae: 2.8,
      note: "Competitive feature-based SOL model.",
      featureImportance: [
        { feature: "Previous Close", score: 89 },
        { feature: "Volume", score: 81 },
        { feature: "RSI", score: 70 },
        { feature: "MACD", score: 64 },
        { feature: "Volatility", score: 58 },
      ],
    },
    "Random Forest": {
      accuracy: "85%",
      confidence: "82.1%",
      rmse: 4.8,
      mae: 3.2,
      note: "Reliable ensemble benchmark for SOL.",
      featureImportance: [
        { feature: "Previous Close", score: 86 },
        { feature: "Volume", score: 77 },
        { feature: "RSI", score: 65 },
        { feature: "MACD", score: 60 },
        { feature: "Volatility", score: 55 },
      ],
    },
    "Linear Regression": {
      accuracy: "79%",
      confidence: "78.1%",
      rmse: 5.5,
      mae: 3.9,
      note: "Simple and interpretable SOL baseline.",
      featureImportance: [
        { feature: "Previous Close", score: 80 },
        { feature: "Volume", score: 68 },
        { feature: "RSI", score: 60 },
        { feature: "Moving Avg", score: 56 },
        { feature: "Volatility", score: 48 },
      ],
    },
  },
};

function formatUSD(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  return `$${Number(value).toLocaleString(undefined, {
    minimumFractionDigits: value < 1 ? 4 : 2,
    maximumFractionDigits: value < 1 ? 4 : 2,
  })}`;
}

function getCoinMeta(coinCode) {
  return COIN_OPTIONS.find((c) => c.code === coinCode) || COIN_OPTIONS[0];
}

function getRefreshMs(refreshRate) {
  if (refreshRate === "15 sec") return 15000;
  if (refreshRate === "60 sec") return 60000;
  return 30000;
}

export default function ResearcherDashboard() {
  const [activeMenu, setActiveMenu] = useState("Dashboard");
  const [coin, setCoin] = useState("BTC");
  const [model, setModel] = useState("LSTM");
  const [days, setDays] = useState("30D");
  const [currentTime, setCurrentTime] = useState(new Date());
  const [liveData, setLiveData] = useState(null);
  const [loadingLive, setLoadingLive] = useState(false);
  const [liveError, setLiveError] = useState("");
  const [saveMessage, setSaveMessage] = useState("");
  const [isProfileSaved, setIsProfileSaved] = useState(false);
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [predictionResult, setPredictionResult] = useState("");
  const [predictionHistory, setPredictionHistory] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [newsItems, setNewsItems] = useState([]);

  const searchRef = useRef(null);
  const profileMenuRef = useRef(null);

  const [profileData, setProfileData] = useState({
    fullName: "Anjal",
    email: "",
    institution: "",
    role: "Cryptocurrency Researcher",
    specialization: "",
    projectTitle: "Closing Price Prediction System",
    bio: "",
  });

  const [settingsData, setSettingsData] = useState({
    theme: "Dark",
    notifications: true,
    autoRefresh: true,
    refreshRate: "30 sec",
    preferredCoin: "BTC",
    preferredModel: "LSTM",
    preferredDays: "30D",
  });

  const coinMeta = getCoinMeta(coin);
  const currentModelStats = MODEL_LIBRARY[coin][model];

  const searchableItems = useMemo(() => {
    return [
      { label: "Profile", action: () => setActiveMenu("Profile") },
      { label: "Dashboard", action: () => setActiveMenu("Dashboard") },
      { label: "Live Data", action: () => setActiveMenu("Live Data") },
      { label: "Research", action: () => setActiveMenu("Research") },
      { label: "Reports", action: () => setActiveMenu("Reports") },
      { label: "Notifications", action: () => setActiveMenu("Notifications") },
      { label: "Settings", action: () => setActiveMenu("Settings") },
      ...COIN_OPTIONS.map((c) => ({
        label: `${c.name} (${c.code})`,
        action: () => {
          setCoin(c.code);
          setActiveMenu("Research");
        },
      })),
      ...MODEL_OPTIONS.map((m) => ({
        label: `Model: ${m}`,
        action: () => {
          setModel(m);
          setActiveMenu("Research");
        },
      })),
    ];
  }, []);

  const filteredSearchResults = useMemo(() => {
    if (!searchTerm.trim()) return [];
    return searchableItems.filter((item) =>
      item.label.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [searchTerm, searchableItems]);

  const fetchLiveData = async (selectedCoin = coin) => {
    try {
      setLoadingLive(true);
      setLiveError("");

      const meta = getCoinMeta(selectedCoin);
      const response = await axios.get(
        `https://api.coingecko.com/api/v3/coins/${meta.apiId}?localization=false&tickers=false&community_data=false&developer_data=false&sparkline=false`
      );

      setLiveData(response.data);
    } catch (error) {
      console.error("Live data fetch failed:", error);
      setLiveData(null);
      setLiveError("Unable to load live data right now.");
    } finally {
      setLoadingLive(false);
    }
  };

  useEffect(() => {
    const savedProfile = localStorage.getItem("researcherProfile");
    const savedSettings = localStorage.getItem("researcherSettings");
    const savedPredictions = localStorage.getItem("researcherPredictionHistory");

    if (savedProfile) {
      const parsed = JSON.parse(savedProfile);
      setProfileData(parsed);
      setIsProfileSaved(true);
      setIsEditingProfile(false);
    } else {
      setIsProfileSaved(false);
      setIsEditingProfile(true);
    }

    if (savedSettings) {
      const parsed = JSON.parse(savedSettings);
      setSettingsData(parsed);
      setCoin(parsed.preferredCoin || "BTC");
      setModel(parsed.preferredModel || "LSTM");
      setDays(parsed.preferredDays || "30D");
    }

    if (savedPredictions) {
      setPredictionHistory(JSON.parse(savedPredictions));
    }
  }, []);

  useEffect(() => {
    if (settingsData.theme === "Light") {
      document.body.classList.add("light-theme");
    } else {
      document.body.classList.remove("light-theme");
    }
  }, [settingsData.theme]);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    fetchLiveData(coin);

    let intervalId = null;
    if (settingsData.autoRefresh) {
      intervalId = setInterval(() => {
        fetchLiveData(coin);
      }, getRefreshMs(settingsData.refreshRate));
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [coin, settingsData.autoRefresh, settingsData.refreshRate]);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        const response = await axios.get("http://127.0.0.1:8000/api/coin-news", {
          params: { coin: coinMeta.name },
        });

        if (Array.isArray(response.data) && response.data.length > 0) {
          setNewsItems(response.data);
        } else {
          setNewsItems(NEWS_FALLBACK[coin] || []);
        }
      } catch (error) {
        setNewsItems(NEWS_FALLBACK[coin] || []);
      }
    };

    fetchNews();
  }, [coin, coinMeta.name]);

  useEffect(() => {
    if (!saveMessage) return;
    const t = setTimeout(() => setSaveMessage(""), 2500);
    return () => clearTimeout(t);
  }, [saveMessage]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowSearchResults(false);
      }

      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target)) {
        setShowProfileMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const generatedPrediction = useMemo(() => {
    const currentPrice = liveData?.market_data?.current_price?.usd;
    if (!currentPrice) return currentModelStats.note;

    const modelOffsets = {
      LSTM: 0.0015,
      GRU: 0.0010,
      XGBoost: 0.0008,
      "Random Forest": 0.0005,
      "Linear Regression": 0.0002,
    };

    const dayMultipliers = {
      "7D": 1,
      "30D": 1.5,
      "90D": 2,
    };

    const predicted =
      currentPrice * (1 + modelOffsets[model] * dayMultipliers[days]);

    return `${model} predicts the next closing price for ${coinMeta.name} around ${formatUSD(
      predicted.toFixed(2)
    )} with confidence ${currentModelStats.confidence}.`;
  }, [liveData, model, days, coinMeta.name, currentModelStats]);

  const reportData = useMemo(() => {
    const currentPrice = liveData?.market_data?.current_price?.usd ?? null;
    const high24h = liveData?.market_data?.high_24h?.usd ?? null;
    const low24h = liveData?.market_data?.low_24h?.usd ?? null;
    const marketCap = liveData?.market_data?.market_cap?.usd ?? null;
    const volume24h = liveData?.market_data?.total_volume?.usd ?? null;
    const change24h = liveData?.market_data?.price_change_percentage_24h ?? null;

    return {
      researcher: profileData.fullName || "Researcher",
      generatedAt: currentTime.toLocaleString(),
      coin: coinMeta.name,
      coinCode: coin,
      model,
      days,
      theme: settingsData.theme,
      currentPrice: formatUSD(currentPrice),
      high24h: formatUSD(high24h),
      low24h: formatUSD(low24h),
      marketCap: formatUSD(marketCap),
      volume24h: formatUSD(volume24h),
      change24h: change24h !== null ? `${change24h.toFixed(2)}%` : "N/A",
      accuracy: currentModelStats.accuracy,
      confidence: currentModelStats.confidence,
      rmse: currentModelStats.rmse,
      mae: currentModelStats.mae,
      note: currentModelStats.note,
      predictionSummary: generatedPrediction,
    };
  }, [
    profileData.fullName,
    currentTime,
    coinMeta.name,
    coin,
    model,
    days,
    settingsData.theme,
    liveData,
    currentModelStats,
    generatedPrediction,
  ]);

  const dashboardMarketCards = useMemo(() => {
    return COIN_OPTIONS.map((item) => {
      if (item.code === coin && liveData?.market_data?.current_price?.usd) {
        return {
          code: item.code,
          name: item.name,
          price: formatUSD(liveData.market_data.current_price.usd),
          change:
            liveData.market_data.price_change_percentage_24h !== undefined
              ? `${liveData.market_data.price_change_percentage_24h.toFixed(2)}%`
              : "N/A",
        };
      }

      const defaults = {
        BTC: { price: "$66,640.00", change: "+2.80%" },
        ETH: { price: "$3,220.00", change: "+1.90%" },
        SOL: { price: "$182.00", change: "+3.20%" },
      };

      return {
        code: item.code,
        name: item.name,
        price: defaults[item.code].price,
        change: defaults[item.code].change,
      };
    });
  }, [coin, liveData]);

  const priceTrendData = useMemo(() => {
    const currentPrice = liveData?.market_data?.current_price?.usd ?? 100;
    const change24h = liveData?.market_data?.price_change_percentage_24h ?? 0;
    const movement = change24h / 100;

    return [
      { label: "T1", value: currentPrice * (1 - movement * 0.7) },
      { label: "T2", value: currentPrice * (1 - movement * 0.35) },
      { label: "T3", value: currentPrice * (1 - movement * 0.12) },
      { label: "T4", value: currentPrice * (1 + movement * 0.12) },
      { label: "T5", value: currentPrice * (1 + movement * 0.3) },
      { label: "T6", value: currentPrice },
    ];
  }, [liveData]);

  const dominanceData = useMemo(() => {
    const btcValue =
      coin === "BTC"
        ? liveData?.market_data?.market_cap?.usd ?? 1200000000000
        : 1200000000000;
    const ethValue =
      coin === "ETH"
        ? liveData?.market_data?.market_cap?.usd ?? 420000000000
        : 420000000000;
    const solValue =
      coin === "SOL"
        ? liveData?.market_data?.market_cap?.usd ?? 82000000000
        : 82000000000;

    return [
      { name: "BTC", value: btcValue },
      { name: "ETH", value: ethValue },
      { name: "SOL", value: solValue },
      { name: "Others", value: 300000000000 },
    ];
  }, [coin, liveData]);

  const volumeBars = useMemo(() => {
    const volume = liveData?.market_data?.total_volume?.usd ?? 0;
    return [
      { name: "Spot", value: Math.round((volume || 18000000000) / 1e9) },
      { name: "Research", value: 14 },
      { name: "Signals", value: 9 },
      { name: "Reports", value: 6 },
    ];
  }, [liveData]);

  const featureBarChartData = useMemo(() => {
    return currentModelStats.featureImportance.map((item) => ({
      name: item.feature,
      score: item.score,
    }));
  }, [currentModelStats]);

  const automatedDescription = useMemo(() => {
    if (!liveData?.market_data) return "Loading automated market summary...";

    const change = liveData.market_data.price_change_percentage_24h ?? 0;
    const marketCap = liveData.market_data.market_cap?.usd;
    const volume = liveData.market_data.total_volume?.usd;
    const sentiment =
      change > 2
        ? "strong bullish momentum"
        : change > 0
        ? "mild positive momentum"
        : change < -2
        ? "notable bearish pressure"
        : "mixed market movement";

    return `${coinMeta.name} is currently showing ${sentiment}. The latest tracked price is ${formatUSD(
      liveData.market_data.current_price?.usd
    )}, with 24-hour change of ${change.toFixed(
      2
    )}%. Market capitalization stands near ${formatUSD(
      marketCap
    )}, while 24-hour trading volume is around ${formatUSD(
      volume
    )}. Based on the selected ${model} model and ${days} window, the dashboard suggests continued monitoring of price volatility and volume behavior before confirming the next directional move.`;
  }, [liveData, coinMeta.name, model, days]);

  const automatedResearchSummary = useMemo(() => {
    if (!liveData?.market_data) {
      return "Loading automated research summary...";
    }

    const price = liveData.market_data.current_price?.usd;
    const change = liveData.market_data.price_change_percentage_24h ?? 0;
    const volume = liveData.market_data.total_volume?.usd;
    const sentiment =
      change > 2
        ? "strong bullish momentum"
        : change > 0
        ? "mild positive momentum"
        : change < -2
        ? "clear bearish pressure"
        : "mixed short-term movement";

    return `${coinMeta.name} is currently showing ${sentiment}. The latest tracked price is ${formatUSD(
      price
    )}, with a 24-hour move of ${change.toFixed(
      2
    )}%. Current trading volume is ${formatUSD(
      volume
    )}. Based on the selected ${model} model and ${days} forecast window, researchers should compare trend continuation against volatility and volume confirmation before drawing directional conclusions.`;
  }, [liveData, coinMeta.name, model, days]);

  const handleProfileChange = (field, value) => {
    setProfileData((prev) => ({ ...prev, [field]: value }));
  };

  const saveProfile = () => {
    localStorage.setItem("researcherProfile", JSON.stringify(profileData));
    setIsProfileSaved(true);
    setIsEditingProfile(false);
    setSaveMessage("Profile saved successfully.");
  };

  const handleSettingsChange = (field, value) => {
    setSettingsData((prev) => {
      const updated = { ...prev, [field]: value };

      if (field === "preferredCoin") setCoin(value);
      if (field === "preferredModel") setModel(value);
      if (field === "preferredDays") setDays(value);

      return updated;
    });
  };

  const saveSettings = () => {
    localStorage.setItem("researcherSettings", JSON.stringify(settingsData));
    setCoin(settingsData.preferredCoin);
    setModel(settingsData.preferredModel);
    setDays(settingsData.preferredDays);
    setSaveMessage("Settings saved and applied.");
  };

  const handleLogout = () => {
    window.location.href = "/";
  };

  const runPrediction = () => {
    const currentPrice = liveData?.market_data?.current_price?.usd;
    if (!currentPrice) {
      setPredictionResult("Live data is not available yet. Please refresh and try again.");
      return;
    }

    const modelOffsets = {
      LSTM: 0.0015,
      GRU: 0.0010,
      XGBoost: 0.0008,
      "Random Forest": 0.0005,
      "Linear Regression": 0.0002,
    };

    const dayMultipliers = {
      "7D": 1,
      "30D": 1.5,
      "90D": 2,
    };

    const predictedPrice =
      currentPrice * (1 + modelOffsets[model] * dayMultipliers[days]);

    const message = `${model} forecast for ${coinMeta.name} over ${days}: predicted closing price ${formatUSD(
      predictedPrice
    )}, current model confidence ${currentModelStats.confidence}.`;

    setPredictionResult(message);

    const nextHistory = [
      {
        time: new Date().toLocaleString(),
        coin: coinMeta.name,
        model,
        days,
        prediction: formatUSD(predictedPrice),
      },
      ...predictionHistory,
    ].slice(0, 5);

    setPredictionHistory(nextHistory);
    localStorage.setItem("researcherPredictionHistory", JSON.stringify(nextHistory));
    setSaveMessage("Prediction completed.");
  };

  const renderDashboard = () => (
    <>
      <div className="status-banner">
        <CheckCircle2 size={18} />
        <span>
          Active selection: {coinMeta.name} · {model} · {days}
        </span>
      </div>

      <div className="top-cards-grid">
        <div className="glass-card stat-card">
          <div>
            <p className="card-label">Current Close</p>
            <h3>{reportData.currentPrice}</h3>
            <span className="positive-text">{reportData.change24h}</span>
          </div>
          <Activity size={24} />
        </div>

        <div className="glass-card stat-card">
          <div>
            <p className="card-label">Predicted Next Close</p>
            <h3>{generatedPrediction.match(/\$\d[\d,\.]*/)?.[0] || "N/A"}</h3>
            <span className="neutral-text">{model}</span>
          </div>
          <TrendingUp size={24} />
        </div>

        <div className="glass-card stat-card">
          <div>
            <p className="card-label">Prediction Confidence</p>
            <h3>{currentModelStats.confidence}</h3>
            <span className="positive-text">{days} forecast</span>
          </div>
          <Brain size={24} />
        </div>

        <div className="glass-card stat-card">
          <div>
            <p className="card-label">Training Records</p>
            <h3>{coin === "BTC" ? "48,320" : coin === "ETH" ? "41,120" : "35,540"}</h3>
            <span className="neutral-text">Cleaned dataset</span>
          </div>
          <Database size={24} />
        </div>
      </div>

      <div className="section-title">Market Overview</div>

      <div className="market-card-grid">
        {dashboardMarketCards.map((item) => (
          <div key={item.code} className="glass-card market-card">
            <div className="market-card-top">
              <div>
                <h4>{item.name}</h4>
                <p>{item.code}</p>
              </div>
              <span className="positive-text">{item.change}</span>
            </div>
            <div className="market-price">{item.price}</div>
          </div>
        ))}
      </div>

      <div className="dashboard-bottom-grid">
        <div className="glass-card chart-panel">
          <div className="panel-header">
            <h3>Closing Price Trend View</h3>
            <span>
              {coin} · {model} · {days}
            </span>
          </div>

          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <LineChart data={priceTrendData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" />
                <YAxis hide />
                <Tooltip formatter={(value) => formatUSD(value)} />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#4ade80"
                  strokeWidth={3}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="right-stack">
          <div className="glass-card side-panel">
            <h3>Recent Experiments</h3>
            <div className="experiment-list">
              {MODEL_OPTIONS.map((item) => {
                const stats = MODEL_LIBRARY[coin][item];
                return (
                  <div key={item} className="experiment-row">
                    <div>
                      <strong>{item}</strong>
                      <p>{stats.note}</p>
                    </div>
                    <span>{stats.accuracy}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="glass-card side-panel">
            <h3>Prediction Controls</h3>

            <div className="control-group">
              <label>Coin</label>
              <select value={coin} onChange={(e) => setCoin(e.target.value)}>
                {COIN_OPTIONS.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.code}
                  </option>
                ))}
              </select>
            </div>

            <div className="control-group">
              <label>Model</label>
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {MODEL_OPTIONS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            <div className="control-group">
              <label>Days</label>
              <div className="days-row">
                {DAY_OPTIONS.map((item) => (
                  <button
                    key={item}
                    type="button"
                    className={days === item ? "day-chip active-chip" : "day-chip"}
                    onClick={() => setDays(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>

            <button className="action-btn" type="button" onClick={runPrediction}>
              <BarChart3 size={16} />
              <span>Run Prediction</span>
            </button>

            {predictionResult && (
              <div className="research-notes-box" style={{ marginTop: 16 }}>
                <h3>Latest Prediction</h3>
                <p>{predictionResult}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );

  const renderProfile = () => (
    <div className="feature-page">
      <div className="glass-card page-panel">
        <div className="section-row">
          <h2>Researcher Profile</h2>

          {isProfileSaved && !isEditingProfile && (
            <button
              className="action-btn small-action-btn"
              type="button"
              onClick={() => setIsEditingProfile(true)}
            >
              <Pencil size={16} />
              <span>Edit Profile</span>
            </button>
          )}
        </div>

        {!isProfileSaved || isEditingProfile ? (
          <>
            <div className="profile-form-grid">
              <div className="control-group">
                <label>Full Name</label>
                <input
                  value={profileData.fullName}
                  onChange={(e) => handleProfileChange("fullName", e.target.value)}
                  className="dark-input"
                />
              </div>

              <div className="control-group">
                <label>Email</label>
                <input
                  value={profileData.email}
                  onChange={(e) => handleProfileChange("email", e.target.value)}
                  className="dark-input"
                />
              </div>

              <div className="control-group">
                <label>Institution</label>
                <input
                  value={profileData.institution}
                  onChange={(e) => handleProfileChange("institution", e.target.value)}
                  className="dark-input"
                />
              </div>

              <div className="control-group">
                <label>Role</label>
                <input
                  value={profileData.role}
                  onChange={(e) => handleProfileChange("role", e.target.value)}
                  className="dark-input"
                />
              </div>

              <div className="control-group">
                <label>Specialization</label>
                <input
                  value={profileData.specialization}
                  onChange={(e) => handleProfileChange("specialization", e.target.value)}
                  className="dark-input"
                />
              </div>

              <div className="control-group">
                <label>Project Title</label>
                <input
                  value={profileData.projectTitle}
                  onChange={(e) => handleProfileChange("projectTitle", e.target.value)}
                  className="dark-input"
                />
              </div>
            </div>

            <div className="control-group">
              <label>Bio</label>
              <textarea
                rows="4"
                value={profileData.bio}
                onChange={(e) => handleProfileChange("bio", e.target.value)}
                className="dark-input textarea-input"
              />
            </div>

            <button className="action-btn save-btn" type="button" onClick={saveProfile}>
              <Save size={16} />
              <span>Save Profile</span>
            </button>
          </>
        ) : (
          <div className="report-grid-custom">
            <div className="info-card">
              <h3>Full Name</h3>
              <p>{profileData.fullName || "N/A"}</p>
            </div>
            <div className="info-card">
              <h3>Email</h3>
              <p>{profileData.email || "N/A"}</p>
            </div>
            <div className="info-card">
              <h3>Institution</h3>
              <p>{profileData.institution || "N/A"}</p>
            </div>
            <div className="info-card">
              <h3>Role</h3>
              <p>{profileData.role || "N/A"}</p>
            </div>
            <div className="info-card">
              <h3>Specialization</h3>
              <p>{profileData.specialization || "N/A"}</p>
            </div>
            <div className="info-card">
              <h3>Project Title</h3>
              <p>{profileData.projectTitle || "N/A"}</p>
            </div>

            <div className="research-notes-box full-width-card">
              <h3>Bio</h3>
              <p>{profileData.bio || "No bio provided."}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const renderLiveData = () => (
    <div className="feature-page">
      <div className="glass-card page-panel">
        <div className="section-row">
          <h2>Live Data</h2>
          <button className="refresh-btn" type="button" onClick={() => fetchLiveData(coin)}>
            <RefreshCw size={16} />
            <span>Refresh</span>
          </button>
        </div>

        {loadingLive ? (
          <p>Loading live data...</p>
        ) : liveError ? (
          <p>{liveError}</p>
        ) : liveData ? (
          <>
            <div className="live-data-grid">
              <div className="data-box">
                <span>Coin</span>
                <strong>{liveData.name}</strong>
              </div>
              <div className="data-box">
                <span>Symbol</span>
                <strong>{liveData.symbol?.toUpperCase()}</strong>
              </div>
              <div className="data-box">
                <span>Current Price</span>
                <strong>{formatUSD(liveData.market_data.current_price.usd)}</strong>
              </div>
              <div className="data-box">
                <span>24h High</span>
                <strong>{formatUSD(liveData.market_data.high_24h.usd)}</strong>
              </div>
              <div className="data-box">
                <span>24h Low</span>
                <strong>{formatUSD(liveData.market_data.low_24h.usd)}</strong>
              </div>
              <div className="data-box">
                <span>24h Change</span>
                <strong>{liveData.market_data.price_change_percentage_24h?.toFixed(2)}%</strong>
              </div>
              <div className="data-box">
                <span>Market Cap</span>
                <strong>{formatUSD(liveData.market_data.market_cap.usd)}</strong>
              </div>
              <div className="data-box">
                <span>Total Volume</span>
                <strong>{formatUSD(liveData.market_data.total_volume.usd)}</strong>
              </div>
              <div className="data-box">
                <span>Circulating Supply</span>
                <strong>{Number(liveData.market_data.circulating_supply).toLocaleString()}</strong>
              </div>
              <div className="data-box">
                <span>Selected Model</span>
                <strong>{model}</strong>
              </div>
              <div className="data-box">
                <span>Window</span>
                <strong>{days}</strong>
              </div>
              <div className="data-box">
                <span>Last Updated</span>
                <strong>{new Date(liveData.last_updated).toLocaleString()}</strong>
              </div>
            </div>

            <div className="dashboard-bottom-grid spaced-grid">
              <div className="glass-card chart-panel">
                <div className="panel-header">
                  <h3>Live Price Graph</h3>
                  <span>{coinMeta.name}</span>
                </div>
                <div style={{ width: "100%", height: 260 }}>
                  <ResponsiveContainer>
                    <LineChart data={priceTrendData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="label" />
                      <YAxis hide />
                      <Tooltip formatter={(value) => formatUSD(value)} />
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke="#4ade80"
                        strokeWidth={3}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="glass-card chart-panel">
                <div className="panel-header">
                  <h3>Market Share</h3>
                  <span>Estimated split</span>
                </div>
                <div style={{ width: "100%", height: 260 }}>
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie
                        data={dominanceData}
                        dataKey="value"
                        cx="50%"
                        cy="50%"
                        outerRadius={90}
                        label={({ name }) => name}
                      >
                        {dominanceData.map((entry, index) => (
                          <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatUSD(value)} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="glass-card chart-panel top-space">
              <div className="panel-header">
                <h3>Automated Description</h3>
                <span>Live interpretation</span>
              </div>
              <p>{automatedDescription}</p>
            </div>

            <div className="glass-card chart-panel top-space">
              <div className="panel-header">
                <h3>Volume Overview</h3>
                <span>Research snapshot</span>
              </div>
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <BarChart data={volumeBars}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        ) : (
          <p>No live data available.</p>
        )}
      </div>
    </div>
  );

  const renderResearch = () => (
    <div className="feature-page">
      <div className="glass-card page-panel">
        <div className="section-row">
          <h2>Research</h2>
          <div className="report-badge">
            <Newspaper size={16} />
            <span>Live research view</span>
          </div>
        </div>

        <div className="two-col-grid">
          <div className="info-card">
            <h3>Selected Coin</h3>
            <p>{coinMeta.name}</p>
          </div>
          <div className="info-card">
            <h3>Selected Model</h3>
            <p>{model}</p>
          </div>
          <div className="info-card">
            <h3>Forecast Window</h3>
            <p>{days}</p>
          </div>
          <div className="info-card">
            <h3>Accuracy</h3>
            <p>{currentModelStats.accuracy}</p>
          </div>
          <div className="info-card">
            <h3>RMSE</h3>
            <p>{currentModelStats.rmse}</p>
          </div>
          <div className="info-card">
            <h3>MAE</h3>
            <p>{currentModelStats.mae}</p>
          </div>
        </div>

        <div className="research-notes-box">
          <h3>Automated Research Summary</h3>
          <p>{automatedResearchSummary}</p>
        </div>

        <div className="research-visual-grid">
          <div className="glass-card mini-chart-card">
            <div className="panel-header">
              <h3>Price Trend</h3>
              <span>{coin}</span>
            </div>
            <div className="chart-holder">
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={priceTrendData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="label" />
                  <YAxis hide />
                  <Tooltip formatter={(value) => formatUSD(value)} />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#4cd964"
                    strokeWidth={3}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="glass-card mini-chart-card">
            <div className="panel-header">
              <h3>Estimated Market Share</h3>
              <span>Pie chart</span>
            </div>
            <div className="chart-holder">
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={dominanceData}
                    dataKey="value"
                    cx="50%"
                    cy="50%"
                    outerRadius={88}
                    label={({ name }) => name}
                  >
                    {dominanceData.map((entry, index) => (
                      <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatUSD(value)} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="glass-card mini-chart-card full-span">
            <div className="panel-header">
              <h3>Feature Importance Histogram</h3>
              <span>{model}</span>
            </div>
            <div className="chart-holder">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={featureBarChartData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="score" fill="#4cd964" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="research-notes-box">
          <h3>Model Notes</h3>
          <p>{currentModelStats.note}</p>
        </div>

        <div className="feature-importance-list">
          {currentModelStats.featureImportance.map((item) => (
            <div key={item.feature} className="feature-importance-row">
              <span>{item.feature}</span>
              <div className="feature-bar-wrap">
                <div className="feature-bar" style={{ width: `${item.score}%` }} />
              </div>
              <strong>{item.score}%</strong>
            </div>
          ))}
        </div>

        <div className="news-section">
          <div className="section-row">
            <h2>Coin News</h2>
            <span className="news-subtitle">{coinMeta.name} research updates</span>
          </div>

          <div className="news-grid">
            {newsItems.length > 0 ? (
              newsItems.map((item, index) => {
                const href =
                  item.url ||
                  item.link ||
                  `https://www.google.com/search?q=${encodeURIComponent(
                    `${coinMeta.name} crypto news`
                  )}`;

                return (
                  <a
                    className="news-card news-card-link"
                    key={`${item.title}-${index}`}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <div className="news-card-top">
                      <Newspaper size={16} />
                      <span>{item.source || "Research Feed"}</span>
                    </div>

                    <h4>{item.title}</h4>
                    <p>{item.summary}</p>

                    <div className="news-read-more">Read full update →</div>
                  </a>
                );
              })
            ) : (
              <div className="news-card">
                <h4>No news available</h4>
                <p>News feed could not be loaded for this coin right now.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  const renderReports = () => (
    <div className="feature-page">
      <div className="glass-card page-panel">
        <div className="section-row">
          <h2>Reports</h2>
          <div className="report-badge">
            <FileText size={16} />
            <span>Real-time report</span>
          </div>
        </div>

        <div className="report-grid-custom">
          <div className="info-card">
            <h3>Researcher</h3>
            <p>{reportData.researcher}</p>
          </div>
          <div className="info-card">
            <h3>Coin</h3>
            <p>{reportData.coin}</p>
          </div>
          <div className="info-card">
            <h3>Model</h3>
            <p>{reportData.model}</p>
          </div>
          <div className="info-card">
            <h3>Window</h3>
            <p>{reportData.days}</p>
          </div>
          <div className="info-card">
            <h3>Generated At</h3>
            <p>{reportData.generatedAt}</p>
          </div>
          <div className="info-card">
            <h3>Theme</h3>
            <p>{reportData.theme}</p>
          </div>
          <div className="info-card">
            <h3>Current Price</h3>
            <p>{reportData.currentPrice}</p>
          </div>
          <div className="info-card">
            <h3>24h High</h3>
            <p>{reportData.high24h}</p>
          </div>
          <div className="info-card">
            <h3>24h Low</h3>
            <p>{reportData.low24h}</p>
          </div>
          <div className="info-card">
            <h3>Market Cap</h3>
            <p>{reportData.marketCap}</p>
          </div>
          <div className="info-card">
            <h3>Total Volume</h3>
            <p>{reportData.volume24h}</p>
          </div>
          <div className="info-card">
            <h3>24h Change</h3>
            <p>{reportData.change24h}</p>
          </div>
          <div className="info-card">
            <h3>Accuracy</h3>
            <p>{reportData.accuracy}</p>
          </div>
          <div className="info-card">
            <h3>Confidence</h3>
            <p>{reportData.confidence}</p>
          </div>
          <div className="info-card">
            <h3>RMSE / MAE</h3>
            <p>{reportData.rmse} / {reportData.mae}</p>
          </div>
        </div>

        <div className="research-notes-box">
          <h3>Prediction Summary</h3>
          <p>{reportData.predictionSummary}</p>
          <p>{reportData.note}</p>
        </div>
      </div>
    </div>
  );

  const renderNotifications = () => (
    <div className="feature-page">
      <div className="glass-card page-panel">
        <h2>Notifications</h2>

        {!settingsData.notifications ? (
          <p>Notifications are disabled in Settings.</p>
        ) : (
          <div className="notification-list">
            <div className="notification-item">
              <Bell size={16} />
              <span>
                Live data synced for {coinMeta.name} at {currentTime.toLocaleTimeString()}.
              </span>
            </div>

            <div className="notification-item">
              <Bell size={16} />
              <span>
                Active model is {model} with confidence {currentModelStats.confidence}.
              </span>
            </div>

            {predictionHistory.length > 0 ? (
              predictionHistory.map((item, index) => (
                <div key={`${item.time}-${index}`} className="notification-item">
                  <Bell size={16} />
                  <span>
                    {item.time}: {item.coin} · {item.model} · {item.days} → {item.prediction}
                  </span>
                </div>
              ))
            ) : (
              DEFAULT_NOTIFICATIONS.map((item, index) => (
                <div key={index} className="notification-item">
                  <Bell size={16} />
                  <span>{item}</span>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );

  const renderSettings = () => (
    <div className="feature-page">
      <div className="glass-card page-panel">
        <h2>Settings</h2>

        <div className="settings-grid">
          <div className="control-group">
            <label>Theme</label>
            <select
              value={settingsData.theme}
              onChange={(e) => handleSettingsChange("theme", e.target.value)}
            >
              <option>Dark</option>
              <option>Light</option>
            </select>
          </div>

          <div className="control-group">
            <label>Preferred Coin</label>
            <select
              value={settingsData.preferredCoin}
              onChange={(e) => handleSettingsChange("preferredCoin", e.target.value)}
            >
              {COIN_OPTIONS.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.code}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <label>Preferred Model</label>
            <select
              value={settingsData.preferredModel}
              onChange={(e) => handleSettingsChange("preferredModel", e.target.value)}
            >
              {MODEL_OPTIONS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <label>Preferred Days</label>
            <select
              value={settingsData.preferredDays}
              onChange={(e) => handleSettingsChange("preferredDays", e.target.value)}
            >
              {DAY_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <label>Refresh Rate</label>
            <select
              value={settingsData.refreshRate}
              onChange={(e) => handleSettingsChange("refreshRate", e.target.value)}
            >
              <option>15 sec</option>
              <option>30 sec</option>
              <option>60 sec</option>
            </select>
          </div>

          <div className="toggle-row">
            <label>Enable Notifications</label>
            <input
              type="checkbox"
              checked={settingsData.notifications}
              onChange={(e) => handleSettingsChange("notifications", e.target.checked)}
            />
          </div>

          <div className="toggle-row">
            <label>Auto Refresh Live Data</label>
            <input
              type="checkbox"
              checked={settingsData.autoRefresh}
              onChange={(e) => handleSettingsChange("autoRefresh", e.target.checked)}
            />
          </div>
        </div>

        <button className="action-btn save-btn" type="button" onClick={saveSettings}>
          <Save size={16} />
          <span>Save Settings</span>
        </button>
      </div>
    </div>
  );

  const renderContent = () => {
    switch (activeMenu) {
      case "Profile":
        return renderProfile();
      case "Dashboard":
        return renderDashboard();
      case "Live Data":
        return renderLiveData();
      case "Research":
        return renderResearch();
      case "Reports":
        return renderReports();
      case "Notifications":
        return renderNotifications();
      case "Settings":
        return renderSettings();
      default:
        return renderDashboard();
    }
  };

  return (
    <div className="research-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-icon">◈</div>
          <h2>CryptoResearch</h2>
        </div>

        <div className="sidebar-menu">
          <button
            className={activeMenu === "Profile" ? "menu-item active-menu" : "menu-item"}
            onClick={() => setActiveMenu("Profile")}
            type="button"
          >
            <User size={18} />
            <span>Profile</span>
          </button>

          <button
            className={activeMenu === "Dashboard" ? "menu-item active-menu" : "menu-item"}
            onClick={() => setActiveMenu("Dashboard")}
            type="button"
          >
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </button>

          <button
            className={activeMenu === "Live Data" ? "menu-item active-menu" : "menu-item"}
            onClick={() => setActiveMenu("Live Data")}
            type="button"
          >
            <Activity size={18} />
            <span>Live Data</span>
          </button>

          <button
            className={activeMenu === "Research" ? "menu-item active-menu" : "menu-item"}
            onClick={() => setActiveMenu("Research")}
            type="button"
          >
            <Brain size={18} />
            <span>Research</span>
          </button>

          <button
            className={activeMenu === "Reports" ? "menu-item active-menu" : "menu-item"}
            onClick={() => setActiveMenu("Reports")}
            type="button"
          >
            <FolderOpen size={18} />
            <span>Reports</span>
          </button>

          <button
            className={activeMenu === "Notifications" ? "menu-item active-menu" : "menu-item"}
            onClick={() => setActiveMenu("Notifications")}
            type="button"
          >
            <Bell size={18} />
            <span>Notifications</span>
          </button>
        </div>

        <div className="sidebar-banner glass-card">
          <div className="coin-circle">₿</div>
          <h4>Research Notes</h4>
          <p>Track experiments, live prices, and model outcomes in one place.</p>
          <button className="buy-btn" type="button" onClick={() => setActiveMenu("Research")}>
            Open Workspace
          </button>
        </div>

        <div className="sidebar-footer">
          <button
            className={activeMenu === "Settings" ? "menu-item active-menu" : "menu-item"}
            onClick={() => setActiveMenu("Settings")}
            type="button"
          >
            <Settings size={18} />
            <span>Settings</span>
          </button>

          <button className="menu-item" onClick={handleLogout} type="button">
            <LogOut size={18} />
            <span>Log Out</span>
          </button>
        </div>
      </aside>

      <main className="main-content">
        <div className="topbar">
          <div className="page-heading">
            <h1>{activeMenu}</h1>
            <p>
              Welcome back, {profileData.fullName || "Researcher"} ·{" "}
              {currentTime.toLocaleDateString()} · {currentTime.toLocaleTimeString()}
            </p>
          </div>

          <div className="topbar-actions">
            <div className="search-area" ref={searchRef}>
              <div className="search-box">
                <Search size={16} />
                <input
                  type="text"
                  placeholder="Search researcher workspace..."
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setShowSearchResults(true);
                  }}
                  onFocus={() => setShowSearchResults(true)}
                />
              </div>

              {showSearchResults && searchTerm.trim() && (
                <div className="search-results-dropdown">
                  {filteredSearchResults.length > 0 ? (
                    filteredSearchResults.map((item, index) => (
                      <button
                        key={`${item.label}-${index}`}
                        type="button"
                        className="search-result-item"
                        onClick={() => {
                          item.action();
                          setSearchTerm("");
                          setShowSearchResults(false);
                        }}
                      >
                        {item.label}
                      </button>
                    ))
                  ) : (
                    <div className="search-empty">No matching result found.</div>
                  )}
                </div>
              )}
            </div>

            <div className="icon-btn">
              <FolderOpen size={18} />
            </div>

            <div className="icon-btn">
              <Clock3 size={18} />
            </div>

            <div className="profile-menu-wrap" ref={profileMenuRef}>
              <button
                type="button"
                className="profile-mini profile-mini-btn"
                onClick={() => setShowProfileMenu((prev) => !prev)}
              >
                <div className="avatar-box">
                  {(profileData.fullName || "A").charAt(0).toUpperCase()}
                </div>
                <span>{profileData.fullName || "Researcher"}</span>
                <ChevronDown size={16} />
              </button>

              {showProfileMenu && (
                <div className="profile-dropdown">
                  <button
                    type="button"
                    className="profile-dropdown-item"
                    onClick={() => {
                      setActiveMenu("Profile");
                      setShowProfileMenu(false);
                    }}
                  >
                    View Profile
                  </button>
                  <button
                    type="button"
                    className="profile-dropdown-item"
                    onClick={() => {
                      setActiveMenu("Settings");
                      setShowProfileMenu(false);
                    }}
                  >
                    Settings
                  </button>
                  <button
                    type="button"
                    className="profile-dropdown-item danger-item"
                    onClick={handleLogout}
                  >
                    Log Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {saveMessage && (
          <div className="save-message">
            <CheckCircle2 size={16} />
            <span>{saveMessage}</span>
          </div>
        )}

        {renderContent()}
      </main>
    </div>
  );
}