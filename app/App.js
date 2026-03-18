import { useState, useRef, useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import {
  StyleSheet,
  Text,
  View,
  FlatList,
  TouchableOpacity,
  Animated,
  Dimensions,
  SafeAreaView,
  Modal,
  Pressable,
  ScrollView,
  PanResponder,
  Linking,
  ActivityIndicator,
} from 'react-native';

const API_URL = 'https://uhhmb07qi5.execute-api.us-east-1.amazonaws.com/stories';

const { width, height } = Dimensions.get('window');

const CATEGORY_COLORS = {
  'World':         '#2563EB',
  'Politics':      '#7C3AED',
  'Business':      '#059669',
  'Tech':          '#0891B2',
  'Science':       '#0E7490',
  'Sports':        '#EA580C',
  'Entertainment': '#DB2777',
  'Gaming':        '#DC2626',
  'Music':         '#9333EA',
  'Climate':       '#65A30D',
};

const THEMES = {
  light: {
    bg:                 '#FFFFFF',
    surface:            '#FFFFFF',
    surfaceAlt:         '#F5F5F5',
    border:             '#EBEBEB',
    borderSubtle:       '#F0F0F0',
    textPrimary:        '#111111',
    textSecondary:      '#333333',
    textMuted:          '#999999',
    textFaint:          '#555555',
    chipBg:             '#F5F5F5',
    chipText:           '#777777',
    filterBtnBg:        '#F5F5F5',
    filterBtnText:      '#444444',
    filterBtnActiveBg:  '#111111',
    filterBtnActiveText:'#FFFFFF',
    filterDropdownBg:   '#FFFFFF',
    filterText:         '#555555',
    filterCheckColor:   '#111111',
    adBg:               '#F5F5F5',
    adBorder:           '#E8E8E8',
    adText:             '#AAAAAA',
    statusBar:          'dark',
  },
  dark: {
    bg:                 '#111111',
    surface:            '#1C1C1C',
    surfaceAlt:         '#252525',
    border:             '#2A2A2A',
    borderSubtle:       '#222222',
    textPrimary:        '#F0F0F0',
    textSecondary:      '#CCCCCC',
    textMuted:          '#666666',
    textFaint:          '#AAAAAA',
    chipBg:             '#2A2A2A',
    chipText:           '#999999',
    filterBtnBg:        '#2A2A2A',
    filterBtnText:      '#BBBBBB',
    filterBtnActiveBg:  '#F0F0F0',
    filterBtnActiveText:'#111111',
    filterDropdownBg:   '#1C1C1C',
    filterText:         '#AAAAAA',
    filterCheckColor:   '#F0F0F0',
    adBg:               '#1C1C1C',
    adBorder:           '#222222',
    adText:             '#555555',
    statusBar:          'light',
  },
};

const categoryColor = (cat) => CATEGORY_COLORS[cat] || '#6B7280';
const cleanSummary = (text = '') => text.replace(/^#+\s+[\w\s]+\n+/i, '').trim();

const AdBanner = ({ t }) => (
  <View style={[styles.adBanner, { backgroundColor: t.adBg, borderTopColor: t.adBorder }]}>
    <Text style={[styles.adLabel, { color: t.adText, borderColor: t.adBorder }]}>Ad</Text>
    <Text style={[styles.adText, { color: t.adText }]}>Your ad could live here</Text>
  </View>
);

export default function App() {
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedStory, setSelectedStory] = useState(null);
  const [selectedCategories, setSelectedCategories] = useState(new Set());
  const [filterVisible, setFilterVisible] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  const t = THEMES[darkMode ? 'dark' : 'light'];

  const fetchStories = (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    fetch(API_URL)
      .then((res) => res.json())
      .then((data) => setStories(data.sort((a, b) => b.sourceCount - a.sourceCount)))
      .finally(() => { setLoading(false); setRefreshing(false); });
  };

  useEffect(() => { fetchStories(); }, []);

  const CATEGORY_ORDER = ['All', 'World', 'Politics', 'Business', 'Tech', 'Science', 'Sports', 'Entertainment', 'Gaming', 'Music', 'Climate'];
  const activeCategories = new Set(stories.map((c) => c.category));
  const categories = CATEGORY_ORDER.filter((c) => c === 'All' || activeCategories.has(c));

  const slideAnim = useRef(new Animated.Value(width)).current;

  const openStory = (story) => {
    setSelectedStory(story);
    slideAnim.setValue(width);
    Animated.timing(slideAnim, { toValue: 0, duration: 280, useNativeDriver: true }).start();
  };

  const closeStory = () => {
    Animated.timing(slideAnim, { toValue: width, duration: 280, useNativeDriver: true })
      .start(() => setSelectedStory(null));
  };

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, { dx, dy }) => dx > 10 && Math.abs(dx) > Math.abs(dy),
      onPanResponderMove: (_, { dx }) => { if (dx > 0) slideAnim.setValue(dx); },
      onPanResponderRelease: (_, { dx, vx }) => {
        if (dx > width * 0.35 || vx > 0.5) {
          Animated.timing(slideAnim, { toValue: width, duration: 200, useNativeDriver: true })
            .start(() => setSelectedStory(null));
        } else {
          Animated.spring(slideAnim, { toValue: 0, useNativeDriver: true }).start();
        }
      },
    })
  ).current;

  const filteredStories = selectedCategories.size === 0
    ? stories
    : stories.filter((s) => selectedCategories.has(s.category));

  const toggleCategory = (cat) => {
    setSelectedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat); else next.add(cat);
      return next;
    });
  };

  const filterLabel = selectedCategories.size === 0
    ? 'Filter'
    : selectedCategories.size === 1
      ? [...selectedCategories][0]
      : `${selectedCategories.size} selected`;

  const filterActive = selectedCategories.size > 0;

  const renderCard = ({ item: story }) => {
    const color = categoryColor(story.category);
    return (
      <TouchableOpacity
        style={[styles.card, { backgroundColor: t.surface, borderColor: t.border }]}
        onPress={() => openStory(story)}
        activeOpacity={0.75}
      >
        <View style={styles.cardTop}>
          <View style={[styles.categoryPill, { backgroundColor: color + '18' }]}>
            <Text style={[styles.categoryText, { color }]}>{story.category}</Text>
          </View>
          {story.sourceCount > 1 && (
            <View style={[styles.multiSourceBadge, { backgroundColor: color + '18' }]}>
              <Text style={[styles.multiSourceText, { color }]}>{story.sourceCount} sources</Text>
            </View>
          )}
        </View>

        <Text style={[styles.cardTitle, { color: t.textPrimary }]}>{story.mergedTitle}</Text>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.sourcesScroll} contentContainerStyle={styles.sourcesScrollContent}>
          {[...new Set(story.articles.map((a) => a.source))].map((source) => (
            <View key={source} style={[styles.sourceChip, { backgroundColor: t.chipBg }]}>
              <Text style={[styles.sourceChipText, { color: t.chipText }]}>{source}</Text>
            </View>
          ))}
        </ScrollView>
      </TouchableOpacity>
    );
  };

  const renderStoryDetail = (story) => {
    const color = categoryColor(story.category);
    const summary = cleanSummary(story.mergedSummary || '');
    return (
      <SafeAreaView style={[{ flex: 1 }, { backgroundColor: t.bg }]}>
        <TouchableOpacity onPress={closeStory} style={styles.backButton}>
          <Text style={[styles.backText, { color: t.textPrimary }]}>← Back</Text>
        </TouchableOpacity>

        <ScrollView contentContainerStyle={styles.detailContent}>
          <View style={[styles.categoryPill, { backgroundColor: color + '18', marginBottom: 16 }]}>
            <Text style={[styles.categoryText, { color }]}>{story.category}</Text>
          </View>

          <Text style={[styles.detailTitle, { color: t.textPrimary }]}>{story.mergedTitle}</Text>
          <Text style={[styles.articleSummary, { color: t.textSecondary }]}>{summary}</Text>

          <View style={[styles.sourcesDivider, { borderTopColor: color + '30' }]}>
            <Text style={[styles.sourcesLabel, { color }]}>Read more</Text>
          </View>

          <ScrollView style={styles.sourceLinksScroll} nestedScrollEnabled showsVerticalScrollIndicator>
            {story.articles.map((article, i) => (
              <TouchableOpacity
                key={`${i}-${article.url}`}
                style={[styles.sourceLink, { borderBottomColor: t.borderSubtle }]}
                onPress={() => Linking.openURL(article.url)}
              >
                <Text style={[styles.sourceLinkName, { color: t.textPrimary }]}>{article.source}</Text>
                <Text style={[styles.sourceLinkArrow, { color }]}>↗</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </ScrollView>

        <AdBanner t={t} />
      </SafeAreaView>
    );
  };

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: t.bg }]}>
      <StatusBar style={t.statusBar} />

      {/* Header */}
      <View style={[styles.header, { borderBottomColor: t.borderSubtle }]}>
        <Text style={[styles.headerTitle, { color: t.textPrimary }]}>News Bites</Text>
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={() => setDarkMode((d) => !d)} style={[styles.themeToggle, { backgroundColor: t.surfaceAlt }]}>
            <Text style={styles.themeToggleIcon}>{darkMode ? '☀︎' : '☽'}</Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => setFilterVisible(true)}
            style={[styles.filterButton, { backgroundColor: filterActive ? t.filterBtnActiveBg : t.filterBtnBg }]}
          >
            <Text style={[styles.filterButtonText, { color: filterActive ? t.filterBtnActiveText : t.filterBtnText }]}>
              {filterLabel} ▾
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Feed */}
      {loading ? (
        <ActivityIndicator style={{ marginTop: 60 }} size="large" color={t.textPrimary} />
      ) : (
        <FlatList
          data={filteredStories}
          keyExtractor={(item) => item.storyId}
          contentContainerStyle={styles.feed}
          renderItem={renderCard}
          refreshing={refreshing}
          onRefresh={() => fetchStories(true)}
        />
      )}

      <AdBanner t={t} />

      {/* Filter Dropdown */}
      <Modal
        visible={filterVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setFilterVisible(false)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setFilterVisible(false)}>
          <Pressable style={[styles.filterDropdown, { backgroundColor: t.filterDropdownBg }]} onPress={(e) => e.stopPropagation()}>
            <TouchableOpacity style={styles.filterOption} onPress={() => setSelectedCategories(new Set())}>
              <Text style={[styles.filterOptionText, { color: selectedCategories.size === 0 ? t.textPrimary : t.filterText }, selectedCategories.size === 0 && styles.filterOptionActive]}>
                All
              </Text>
              {selectedCategories.size === 0 && <Text style={[styles.filterCheck, { color: t.filterCheckColor }]}>✓</Text>}
            </TouchableOpacity>
            <View style={[styles.filterDivider, { backgroundColor: t.borderSubtle }]} />
            {categories.filter((c) => c !== 'All').map((cat) => {
              const active = selectedCategories.has(cat);
              const color = categoryColor(cat);
              return (
                <TouchableOpacity key={cat} style={styles.filterOption} onPress={() => toggleCategory(cat)}>
                  <View style={styles.filterOptionRow}>
                    <View style={[styles.filterDot, { backgroundColor: active ? color : t.border }]} />
                    <Text style={[styles.filterOptionText, { color: active ? t.textPrimary : t.filterText }, active && styles.filterOptionActive]}>
                      {cat}
                    </Text>
                  </View>
                  {active && <Text style={[styles.filterCheck, { color }]}>✓</Text>}
                </TouchableOpacity>
              );
            })}
          </Pressable>
        </Pressable>
      </Modal>

      {/* Story Detail */}
      {selectedStory && (
        <Animated.View
          style={[styles.detail, { backgroundColor: t.bg, transform: [{ translateX: slideAnim }] }]}
          {...panResponder.panHandlers}
        >
          {renderStoryDetail(selectedStory)}
        </Animated.View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 1,
  },
  headerTitle: { fontSize: 22, fontWeight: '700' },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  themeToggle: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  themeToggleIcon: { fontSize: 16 },
  filterButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  filterButtonText: { fontSize: 13, fontWeight: '600' },
  feed: { padding: 16, gap: 12 },
  card: {
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    gap: 8,
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  categoryPill: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
    alignSelf: 'flex-start',
  },
  categoryText: {
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  multiSourceBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 20 },
  multiSourceText: { fontSize: 11, fontWeight: '700' },
  cardTitle: { fontSize: 17, fontWeight: '700', lineHeight: 24 },
  sourcesScroll: { marginTop: 2 },
  sourcesScrollContent: { flexDirection: 'row', gap: 6, paddingRight: 4 },
  sourceChip: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 },
  sourceChipText: { fontSize: 11, fontWeight: '500' },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.3)',
    justifyContent: 'flex-start',
    alignItems: 'flex-end',
    paddingTop: 90,
    paddingRight: 16,
  },
  filterDropdown: {
    borderRadius: 12,
    paddingVertical: 6,
    minWidth: 180,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 8,
  },
  filterOption: {
    paddingHorizontal: 16,
    paddingVertical: 11,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  filterOptionRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  filterDot: { width: 8, height: 8, borderRadius: 4 },
  filterOptionText: { fontSize: 15, fontWeight: '500' },
  filterOptionActive: { fontWeight: '700' },
  filterCheck: { fontSize: 14, fontWeight: '700' },
  filterDivider: { height: 1, marginHorizontal: 16, marginVertical: 2 },
  adBanner: {
    height: 60,
    borderTopWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  adLabel: {
    fontSize: 10,
    fontWeight: '700',
    borderWidth: 1,
    borderRadius: 3,
    paddingHorizontal: 4,
    paddingVertical: 1,
    letterSpacing: 0.5,
  },
  adText: { fontSize: 13, fontWeight: '500' },
  detail: { ...StyleSheet.absoluteFillObject },
  backButton: { paddingHorizontal: 20, paddingVertical: 14 },
  backText: { fontSize: 16, fontWeight: '600' },
  detailContent: { paddingHorizontal: 24, paddingTop: 8, paddingBottom: 60 },
  detailTitle: { fontSize: 26, fontWeight: '800', lineHeight: 34, marginBottom: 24 },
  articleSummary: { fontSize: 16, lineHeight: 26, marginBottom: 28 },
  sourcesDivider: { borderTopWidth: 1, paddingTop: 16, marginBottom: 12 },
  sourcesLabel: { fontSize: 11, fontWeight: '800', textTransform: 'uppercase', letterSpacing: 0.8 },
  sourceLinksScroll: { maxHeight: 194 },
  sourceLink: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  sourceLinkName: { fontSize: 15, fontWeight: '600' },
  sourceLinkArrow: { fontSize: 16, fontWeight: '700' },
});
