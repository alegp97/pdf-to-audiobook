"""Voice catalogue and local model paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VoiceEntry:
    id: str
    display_name: str
    language: str
    locale: str
    gender: str
    engine: str  # "edge", "kokoro", "piper", "sapi"


def _edge(short_name: str, display_name: str, language: str, locale: str, gender: str) -> VoiceEntry:
    return VoiceEntry(short_name, display_name, language, locale, gender, "edge")


def _offline(short_name: str, display_name: str, language: str, locale: str, gender: str, engine: str) -> VoiceEntry:
    return VoiceEntry(short_name, display_name, language, locale, gender, engine)


# Language display names for the combo box. The first group has the richest
# voice coverage in this app, followed by additional Microsoft Edge locales.
LANGUAGE_ORDER = [
    "English", "Spanish", "French", "German", "Portuguese", "Italian",
    "Japanese", "Chinese", "Russian", "Arabic", "Korean", "Hindi",
    "Dutch", "Polish", "Turkish", "Ukrainian", "Greek", "Swedish",
    "Norwegian", "Danish", "Finnish", "Czech", "Hungarian", "Romanian",
    "Thai", "Vietnamese", "Indonesian", "Malay", "Hebrew",
    "Bengali", "Urdu", "Persian", "Filipino", "Tamil", "Telugu",
    "Marathi", "Gujarati", "Kannada", "Malayalam", "Swahili", "Burmese",
    "Javanese", "Punjabi", "Nepali", "Zulu", "Bulgarian", "Croatian",
    "Serbian", "Slovak", "Slovenian", "Lithuanian", "Latvian", "Estonian",
    "Catalan", "Basque", "Galician", "Welsh", "Afrikaans", "Amharic",
]


SAMPLE_TEXTS = {
    "English": (
        "For centuries, civilizations observed the sky in search of answers. "
        "Some saw gods; others saw simple celestial bodies. Yet all shared the "
        "intuition that a hidden order existed behind the movement of the stars. "
        "Over time, that search became science, philosophy, and also technology."
    ),
    "Spanish": (
        "Durante siglos, las civilizaciones observaron el cielo buscando respuestas. "
        "Algunos veian dioses; otros, simples cuerpos celestes. Sin embargo, todos "
        "compartian la intuicion de que existia un orden oculto detras del movimiento "
        "de las estrellas. Con el paso del tiempo, esa busqueda se convirtio en "
        "ciencia, filosofia y tambien en tecnologia."
    ),
    "French": (
        "Pendant des siecles, les civilisations ont observe le ciel en quete de "
        "reponses. Certains y voyaient des dieux; d'autres, de simples corps "
        "celestes. Pourtant, tous partageaient l'intuition qu'un ordre cache "
        "existait derriere le mouvement des etoiles. Avec le temps, cette quete "
        "est devenue science, philosophie, et aussi technologie."
    ),
    "German": (
        "Jahrhundertelang beobachteten Zivilisationen den Himmel auf der Suche "
        "nach Antworten. Einige sahen Gotter; andere nur einfache Himmelskorper. "
        "Doch alle teilten die Ahnung, dass hinter der Bewegung der Sterne eine "
        "verborgene Ordnung existierte. Mit der Zeit wurde diese Suche zu "
        "Wissenschaft, Philosophie und auch Technologie."
    ),
    "Portuguese": (
        "Durante seculos, as civilizacoes observaram o ceu em busca de respostas. "
        "Alguns viam deuses; outros, simples corpos celestes. No entanto, todos "
        "compartilhavam a intuicao de que existia uma ordem oculta por tras do "
        "movimento das estrelas. Com o passar do tempo, essa busca se tornou "
        "ciencia, filosofia e tambem tecnologia."
    ),
    "Italian": (
        "Per secoli, le civilta osservarono il cielo in cerca di risposte. "
        "Alcuni vedevano degli dei; altri, semplici corpi celesti. Tuttavia, "
        "tutti condividevano l'intuizione che esistesse un ordine nascosto dietro "
        "il movimento delle stelle. Con il passare del tempo, quella ricerca "
        "divenne scienza, filosofia e anche tecnologia."
    ),
    "Japanese": (
        "何世紀もの間、文明は答えを求めて空を観察してきました。神々を見た人もいれば、"
        "単なる天体を見た人もいました。しかし誰もが、星の動きの背後には隠れた秩序が"
        "存在するという直感を共有していました。時がたつにつれて、その探求は科学、哲学、"
        "そして技術にもなりました。"
    ),
    "Chinese": (
        "几个世纪以来，各种文明都仰望天空，寻找答案。有些人看见了神灵，另一些人则看见了"
        "普通的天体。然而，所有人都共有一种直觉：在星辰的运动背后，存在着某种隐藏的秩序。"
        "随着时间推移，这种追寻变成了科学、哲学，也变成了技术。"
    ),
    "Russian": (
        "На протяжении веков цивилизации наблюдали за небом в поисках ответов. "
        "Одни видели богов, другие — простые небесные тела. Однако всех объединяло "
        "предчувствие, что за движением звезд скрывается некий порядок. Со временем "
        "этот поиск превратился в науку, философию, а также в технологию."
    ),
    "Arabic": (
        "على مدى قرون، راقبت الحضارات السماء بحثا عن إجابات. رأى بعضهم آلهة، "
        "ورأى آخرون مجرد أجرام سماوية. ومع ذلك، اشترك الجميع في حدس واحد: أن "
        "هناك نظاما خفيا وراء حركة النجوم. ومع مرور الزمن، تحول ذلك البحث إلى "
        "علم وفلسفة، وأيضا إلى تكنولوجيا."
    ),
    "Korean": (
        "수세기 동안 문명들은 해답을 찾기 위해 하늘을 관찰했습니다. 어떤 사람들은 신을 보았고, "
        "다른 사람들은 단순한 천체를 보았습니다. 그러나 모두 별들의 움직임 뒤에 숨겨진 질서가 "
        "있다는 직감을 공유했습니다. 시간이 흐르면서 그 탐구는 과학, 철학, 그리고 기술이 되었습니다."
    ),
    "Hindi": (
        "सदियों तक सभ्यताओं ने उत्तर खोजने के लिए आकाश को देखा। कुछ लोगों ने देवताओं को देखा; "
        "दूसरों ने केवल खगोलीय पिंडों को। फिर भी, सभी में यह सहज बोध था कि तारों की गति के "
        "पीछे कोई छिपी हुई व्यवस्था है। समय के साथ, यह खोज विज्ञान, दर्शन और तकनीक में बदल गई।"
    ),
    "Dutch": (
        "Eeuwenlang keken beschavingen naar de hemel op zoek naar antwoorden. "
        "Sommigen zagen goden; anderen zagen eenvoudige hemellichamen. Toch deelden "
        "zij allemaal het vermoeden dat er achter de beweging van de sterren een "
        "verborgen orde bestond. Na verloop van tijd werd die zoektocht wetenschap, "
        "filosofie en ook technologie."
    ),
    "Polish": (
        "Przez wieki cywilizacje obserwowaly niebo w poszukiwaniu odpowiedzi. "
        "Jedni widzieli bogow, inni jedynie ciala niebieskie. Jednak wszyscy "
        "dzielili intuicje, ze za ruchem gwiazd kryje sie ukryty porzadek. Z "
        "czasem te poszukiwania staly sie nauka, filozofia, a takze technologia."
    ),
    "Turkish": (
        "Yuzyillar boyunca uygarliklar cevap arayarak gokyuzunu izledi. Bazilari "
        "tanrilari gordu; digerleri ise yalnizca gok cisimlerini. Yine de hepsi, "
        "yildizlarin hareketinin ardinda gizli bir duzen olduguna dair sezgiyi "
        "paylasti. Zamanla bu arayis bilime, felsefeye ve teknolojiye donustu."
    ),
    "Ukrainian": (
        "Протягом століть цивілізації спостерігали за небом у пошуках відповідей. "
        "Одні бачили богів, інші — прості небесні тіла. Проте всі поділяли "
        "інтуїцію, що за рухом зірок існує прихований порядок. З часом цей пошук "
        "перетворився на науку, філософію, а також на технологію."
    ),
    "Greek": (
        "Για αιώνες, οι πολιτισμοί παρατηρούσαν τον ουρανό αναζητώντας απαντήσεις. "
        "Κάποιοι έβλεπαν θεούς· άλλοι απλά ουράνια σώματα. Ωστόσο, όλοι μοιράζονταν "
        "τη διαίσθηση ότι υπήρχε μια κρυφή τάξη πίσω από την κίνηση των άστρων. "
        "Με το πέρασμα του χρόνου, αυτή η αναζήτηση έγινε επιστήμη, φιλοσοφία και "
        "επίσης τεχνολογία."
    ),
    "Swedish": (
        "I arhundraden betraktade civilisationer himlen i sokandet efter svar. "
        "Vissa sag gudar; andra sag enkla himlakroppar. Anda delade alla kanslan "
        "av att det fanns en dold ordning bakom stjarnornas rorelse. Med tiden "
        "blev denna sokan till vetenskap, filosofi och aven teknologi."
    ),
    "Norwegian": (
        "I arhundrer observerte sivilisasjoner himmelen pa jakt etter svar. "
        "Noen sa guder; andre sa bare enkle himmellegemer. Likevel delte alle "
        "intuisjonen om at det fantes en skjult orden bak stjernenes bevegelse. "
        "Med tiden ble denne jakten til vitenskap, filosofi og ogsa teknologi."
    ),
    "Danish": (
        "I arhundreder betragtede civilisationer himlen pa jagt efter svar. "
        "Nogle sa guder; andre sa blot himmellegemer. Alligevel delte alle "
        "fornemmelsen af, at der fandtes en skjult orden bag stjernernes bevaegelse. "
        "Med tiden blev denne sogning til videnskab, filosofi og ogsa teknologi."
    ),
    "Finnish": (
        "Vuosisatojen ajan sivilisaatiot tarkkailivat taivasta etsien vastauksia. "
        "Jotkut nakivat jumalia; toiset vain taivaankappaleita. Silti kaikki "
        "jakoivat aavistuksen siita, etta tahtien liikkeen takana oli piilotettu "
        "jarjestys. Ajan myota tuo etsinta muuttui tieteeksi, filosofiaksi ja "
        "myos teknologiaksi."
    ),
    "Czech": (
        "Po staleti civilizace pozorovaly oblohu a hledaly odpovedi. Nekteri "
        "videli bohy; jini pouze nebeska telesa. Presto vsichni sdileli tuseni, "
        "ze za pohybem hvezd existuje skryty rad. Casem se toto hledani zmenilo "
        "ve vedu, filozofii a take technologii."
    ),
    "Hungarian": (
        "Evszazadokon at civilizaciok figyeltek az eget valaszokat keresve. "
        "Egyesek isteneket lattak; masok csupan egitesteket. Megis mindannyian "
        "osztoztak abban a megerzesben, hogy a csillagok mozgasa mogott rejtett "
        "rend letezik. Idovel ez a kereses tudomannya, filozofiava es technologiava valt."
    ),
    "Romanian": (
        "Timp de secole, civilizatiile au observat cerul in cautarea raspunsurilor. "
        "Unii vedeau zei; altii, simple corpuri ceresti. Totusi, toti impartaseau "
        "intuitia ca exista o ordine ascunsa in spatele miscarii stelelor. Cu "
        "trecerea timpului, aceasta cautare a devenit stiinta, filozofie si, de "
        "asemenea, tehnologie."
    ),
    "Thai": (
        "เป็นเวลาหลายศตวรรษ อารยธรรมต่าง ๆ เฝ้ามองท้องฟ้าเพื่อค้นหาคำตอบ "
        "บางคนเห็นเทพเจ้า บางคนเห็นเพียงวัตถุท้องฟ้าเท่านั้น อย่างไรก็ตาม "
        "ทุกคนมีสัญชาตญาณร่วมกันว่า มีระเบียบที่ซ่อนอยู่เบื้องหลังการเคลื่อนที่ของดวงดาว "
        "เมื่อเวลาผ่านไป การค้นหานั้นกลายเป็นวิทยาศาสตร์ ปรัชญา และเทคโนโลยีด้วย"
    ),
    "Vietnamese": (
        "Trong nhiều thế kỷ, các nền văn minh đã quan sát bầu trời để tìm kiếm câu trả lời. "
        "Một số người nhìn thấy các vị thần; những người khác chỉ thấy các thiên thể. "
        "Tuy vậy, tất cả đều có chung trực giác rằng có một trật tự ẩn giấu phía sau "
        "chuyển động của các vì sao. Theo thời gian, cuộc tìm kiếm ấy trở thành khoa học, "
        "triết học và cả công nghệ."
    ),
    "Indonesian": (
        "Selama berabad-abad, berbagai peradaban mengamati langit untuk mencari jawaban. "
        "Sebagian melihat dewa-dewa; yang lain hanya melihat benda-benda langit. Namun, "
        "semuanya berbagi intuisi bahwa ada tatanan tersembunyi di balik gerak bintang-bintang. "
        "Seiring waktu, pencarian itu menjadi ilmu pengetahuan, filsafat, dan juga teknologi."
    ),
    "Malay": (
        "Selama berabad-abad, tamadun memerhatikan langit untuk mencari jawapan. "
        "Ada yang melihat dewa-dewa; yang lain hanya melihat jasad-jasad samawi. "
        "Namun, semuanya berkongsi naluri bahawa wujud suatu aturan tersembunyi di "
        "sebalik pergerakan bintang-bintang. Lama-kelamaan, pencarian itu menjadi "
        "sains, falsafah dan juga teknologi."
    ),
    "Hebrew": (
        "במשך מאות שנים צפו תרבויות בשמים בחיפוש אחר תשובות. חלקן ראו אלים; "
        "אחרות ראו גופים שמימיים פשוטים. אך כולן חלקו את התחושה שמאחורי תנועת "
        "הכוכבים קיים סדר נסתר. עם הזמן, החיפוש הזה הפך למדע, לפילוסופיה וגם לטכנולוגיה."
    ),
    "Bengali": (
        "শতাব্দীর পর শতাব্দী ধরে সভ্যতাগুলো উত্তর খুঁজতে আকাশের দিকে তাকিয়েছে। "
        "কেউ সেখানে দেবতাদের দেখেছে; কেউ দেখেছে শুধু আকাশের বস্তু। তবু সবারই "
        "মনে হয়েছে, নক্ষত্রের গতির পেছনে একটি লুকানো শৃঙ্খলা আছে। সময়ের সঙ্গে "
        "সঙ্গে সেই অনুসন্ধান বিজ্ঞান, দর্শন এবং প্রযুক্তিতে রূপ নিয়েছে।"
    ),
    "Urdu": (
        "صدیوں تک تہذیبوں نے جواب تلاش کرنے کے لیے آسمان کا مشاہدہ کیا۔ کچھ لوگوں "
        "نے دیوتاؤں کو دیکھا؛ دوسروں نے صرف آسمانی اجسام کو۔ تاہم سب اس احساس میں "
        "شریک تھے کہ ستاروں کی حرکت کے پیچھے کوئی پوشیدہ نظم موجود ہے۔ وقت کے ساتھ "
        "یہ تلاش سائنس، فلسفہ اور ٹیکنالوجی میں بدل گئی۔"
    ),
    "Persian": (
        "قرن‌ها، تمدن‌ها برای یافتن پاسخ به آسمان نگاه کردند. برخی خدایان را "
        "می‌دیدند و برخی دیگر تنها اجرام آسمانی را. با این حال، همه این شهود را "
        "داشتند که پشت حرکت ستارگان نظمی پنهان وجود دارد. با گذشت زمان، این جستجو "
        "به علم، فلسفه و همچنین فناوری تبدیل شد."
    ),
    "Filipino": (
        "Sa loob ng maraming siglo, minasdan ng mga kabihasnan ang langit upang "
        "humanap ng mga sagot. Ang ilan ay nakakita ng mga diyos; ang iba naman ay "
        "simpleng mga katawang makalangit. Gayunman, iisa ang kanilang kutob: may "
        "nakatagong kaayusan sa likod ng galaw ng mga bituin. Sa paglipas ng panahon, "
        "ang paghahanap na iyon ay naging agham, pilosopiya, at teknolohiya."
    ),
    "Tamil": (
        "பல நூற்றாண்டுகளாக, நாகரிகங்கள் பதில்களைத் தேடி வானத்தை நோக்கின. சிலர் "
        "அதில் தெய்வங்களை கண்டனர்; மற்றவர்கள் வெறும் விண்மீன் உடல்களையே கண்டனர். "
        "ஆனால் நட்சத்திரங்களின் இயக்கத்தின் பின்னால் மறைந்த ஒழுங்கு ஒன்று உள்ளது "
        "என்பதை அனைவரும் உணர்ந்தனர். காலப்போக்கில் அந்த தேடல் அறிவியல், தத்துவம் "
        "மற்றும் தொழில்நுட்பமாக மாறியது."
    ),
    "Telugu": (
        "శతాబ్దాలుగా నాగరికతలు సమాధానాల కోసం ఆకాశాన్ని పరిశీలించాయి. కొందరు "
        "దేవతలను చూశారు; మరికొందరు సాధారణ ఖగోళ వస్తువులను మాత్రమే చూశారు. అయినా "
        "నక్షత్రాల కదలికల వెనుక ఒక దాగిన క్రమం ఉందనే భావన అందరిలోనూ ఉండేది. "
        "కాలక్రమేణా ఆ అన్వేషణ శాస్త్రం, తత్వశాస్త్రం మరియు సాంకేతికతగా మారింది."
    ),
    "Marathi": (
        "शतकानुशतके संस्कृतींनी उत्तरांच्या शोधात आकाशाचे निरीक्षण केले. काहींना "
        "देव दिसले; काहींना फक्त आकाशीय वस्तू दिसल्या. तरीही सर्वांना तार्‍यांच्या "
        "हालचालीमागे एक दडलेला क्रम आहे अशी जाणीव होती. काळानुसार हा शोध विज्ञान, "
        "तत्त्वज्ञान आणि तंत्रज्ञानात रूपांतरित झाला."
    ),
    "Gujarati": (
        "સદીઓ સુધી સંસ્કૃતિઓએ જવાબોની શોધમાં આકાશનું નિરીક્ષણ કર્યું. કેટલાકે "
        "દેવતાઓ જોયા; અન્યોએ માત્ર આકાશીય પિંડો જોયા. છતાં સૌને એવી અંતર્જ્ઞાન "
        "હતી કે તારાઓની ગતિ પાછળ કોઈ છુપાયેલો ક્રમ છે. સમય જતા આ શોધ વિજ્ઞાન, "
        "તત્ત્વજ્ઞાન અને ટેકનોલોજીમાં ફેરવાઈ."
    ),
    "Kannada": (
        "ಶತಮಾನಗಳ ಕಾಲ ನಾಗರಿಕತೆಗಳು ಉತ್ತರಗಳಿಗಾಗಿ ಆಕಾಶವನ್ನು ಗಮನಿಸಿದವು. ಕೆಲವರು "
        "ದೇವರನ್ನು ಕಂಡರು; ಇತರರು ಕೇವಲ ಆಕಾಶಕಾಯಗಳನ್ನು ಕಂಡರು. ಆದರೂ ನಕ್ಷತ್ರಗಳ ಚಲನೆಯ "
        "ಹಿಂದೆ ಒಂದು ಮರೆವಿನ ಕ್ರಮವಿದೆ ಎಂಬ ಅನುಭವವನ್ನು ಎಲ್ಲರೂ ಹಂಚಿಕೊಂಡರು. ಕಾಲದೊಂದಿಗೆ "
        "ಆ ಹುಡುಕಾಟ ವಿಜ್ಞಾನ, ತತ್ತ್ವಶಾಸ್ತ್ರ ಮತ್ತು ತಂತ್ರಜ್ಞಾನವಾಯಿತು."
    ),
    "Malayalam": (
        "നൂറ്റാണ്ടുകളോളം സംസ്കാരങ്ങൾ ഉത്തരങ്ങൾ തേടി ആകാശത്തെ നിരീക്ഷിച്ചു. ചിലർ "
        "ദേവന്മാരെ കണ്ടു; മറ്റുള്ളവർ വെറും ആകാശവസ്തുക്കളെ മാത്രം കണ്ടു. എന്നിരുന്നാലും "
        "നക്ഷത്രങ്ങളുടെ ചലനത്തിന് പിന്നിൽ ഒളിഞ്ഞ ഒരു ക്രമമുണ്ടെന്ന ബോധം എല്ലാവർക്കും "
        "ഉണ്ടായിരുന്നു. കാലക്രമേണ ആ തിരച്ചിൽ ശാസ്ത്രം, തത്ത്വചിന്ത, സാങ്കേതികവിദ്യയായി മാറി."
    ),
    "Swahili": (
        "Kwa karne nyingi, ustaarabu mbalimbali uliangalia anga ukitafuta majibu. "
        "Wengine waliona miungu; wengine waliona tu miili ya angani. Hata hivyo, "
        "wote walishiriki hisia kwamba kulikuwa na mpangilio uliofichwa nyuma ya "
        "mwendo wa nyota. Kadiri muda ulivyopita, utafutaji huo ukawa sayansi, "
        "falsafa na pia teknolojia."
    ),
    "Burmese": (
        "ရာစုနှစ်များစွာအတွင်း ယဉ်ကျေးမှုများသည် အဖြေများကိုရှာဖွေရန် မိုးကောင်းကင်ကို "
        "လေ့လာခဲ့ကြသည်။ အချို့က နတ်ဘုရားများကို မြင်ကြပြီး၊ အချို့က ရိုးရိုးမိုးကောင်းကင် "
        "အရာဝတ္ထုများကိုသာ မြင်ကြသည်။ သို့သော် ကြယ်များ၏ လှုပ်ရှားမှုနောက်ကွယ်တွင် "
        "ဖုံးကွယ်ထားသော စနစ်တစ်ခု ရှိသည်ဟူသော ခံစားချက်ကို အားလုံးမျှဝေခဲ့ကြသည်။ "
        "အချိန်ကြာလာသည်နှင့်အမျှ ထိုရှာဖွေမှုသည် သိပ္ပံ၊ ဒဿနနှင့် နည်းပညာ ဖြစ်လာခဲ့သည်။"
    ),
    "Javanese": (
        "Wis pirang-pirang abad, peradaban ngawasi langit kanggo nggoleki wangsulan. "
        "Sawetara ndeleng para dewa; liyane mung ndeleng benda-benda langit. Nanging "
        "kabeh padha duwe pangraos yen ana tatanan sing ndhelik ing balik obahing "
        "lintang-lintang. Suwe-suwe, panggolèkan iku dadi ilmu, filsafat lan uga teknologi."
    ),
    "Punjabi": (
        "ਸਦੀਆਂ ਤੱਕ ਸਭਿਆਚਾਰਾਂ ਨੇ ਜਵਾਬ ਲੱਭਣ ਲਈ ਆਕਾਸ਼ ਨੂੰ ਵੇਖਿਆ। ਕੁਝ ਲੋਕਾਂ ਨੇ ਦੇਵਤੇ "
        "ਵੇਖੇ; ਹੋਰਾਂ ਨੇ ਸਿਰਫ਼ ਆਕਾਸ਼ੀ ਪਿੰਡ ਵੇਖੇ। ਫਿਰ ਵੀ ਸਭ ਨੂੰ ਇਹ ਅਹਿਸਾਸ ਸੀ ਕਿ "
        "ਤਾਰਿਆਂ ਦੀ ਚਾਲ ਦੇ ਪਿੱਛੇ ਕੋਈ ਲੁਕਿਆ ਹੋਇਆ ਕ੍ਰਮ ਹੈ। ਸਮੇਂ ਦੇ ਨਾਲ ਇਹ ਖੋਜ ਵਿਗਿਆਨ, "
        "ਦਰਸ਼ਨ ਅਤੇ ਤਕਨਾਲੋਜੀ ਬਣ ਗਈ।"
    ),
    "Nepali": (
        "शताब्दीयौँसम्म सभ्यताहरूले उत्तर खोज्दै आकाशलाई हेरे। केहीले देवताहरू देखे; "
        "अरूले केवल आकाशीय पिण्डहरू देखे। तर सबैले ताराहरूको गतिका पछाडि कुनै लुकेको "
        "व्यवस्था छ भन्ने अनुभूति साझा गरे। समयसँगै त्यो खोज विज्ञान, दर्शन र प्रविधिमा बदलियो।"
    ),
    "Zulu": (
        "Sekungamakhulu eminyaka, izimpucuko zazibuka isibhakabhaka zifuna izimpendulo. "
        "Abanye babona onkulunkulu; abanye babona nje imizimba yasezulwini. Nokho, bonke "
        "babelana ngomuzwa wokuthi kukhona uhlelo olufihlekile ngemuva kokuhamba kwezinkanyezi. "
        "Ngokuhamba kwesikhathi, lolo phenyo lwaba isayensi, ifilosofi nobuchwepheshe."
    ),
    "Bulgarian": (
        "В продължение на векове цивилизациите наблюдавали небето в търсене на отговори. "
        "Някои виждали богове; други — просто небесни тела. Въпреки това всички споделяли "
        "усещането, че зад движението на звездите съществува скрит ред. С течение на времето "
        "това търсене се превърнало в наука, философия и технология."
    ),
    "Croatian": (
        "Stoljećima su civilizacije promatrale nebo tražeći odgovore. Neki su vidjeli "
        "bogove; drugi tek nebeska tijela. Ipak, svi su dijelili intuiciju da iza kretanja "
        "zvijezda postoji skriveni red. S vremenom se ta potraga pretvorila u znanost, "
        "filozofiju i tehnologiju."
    ),
    "Serbian": (
        "Вековима су цивилизације посматрале небо тражећи одговоре. Неки су видели богове; "
        "други само небеска тела. Ипак, сви су делили осећај да иза кретања звезда постоји "
        "скривени поредак. Временом се та потрага претворила у науку, филозофију и технологију."
    ),
    "Slovak": (
        "Po stáročia civilizácie pozorovali oblohu a hľadali odpovede. Niektorí videli "
        "bohov; iní iba nebeské telesá. Napriek tomu všetci zdieľali tušenie, že za pohybom "
        "hviezd existuje skrytý poriadok. Časom sa toto hľadanie zmenilo na vedu, filozofiu "
        "a technológiu."
    ),
    "Slovenian": (
        "Stoletja so civilizacije opazovale nebo in iskale odgovore. Nekateri so videli "
        "bogove; drugi le nebesna telesa. Kljub temu so vsi delili slutnjo, da za gibanjem "
        "zvezd obstaja skriti red. Sčasoma se je to iskanje spremenilo v znanost, filozofijo "
        "in tehnologijo."
    ),
    "Lithuanian": (
        "Šimtmečius civilizacijos stebėjo dangų ieškodamos atsakymų. Vieni matė dievus; "
        "kiti tik dangaus kūnus. Vis dėlto visi jautė, kad už žvaigždžių judėjimo slypi "
        "paslėpta tvarka. Laikui bėgant šios paieškos virto mokslu, filosofija ir technologija."
    ),
    "Latvian": (
        "Gadsimtiem ilgi civilizācijas vēroja debesis, meklējot atbildes. Daži redzēja "
        "dievus; citi tikai debess ķermeņus. Tomēr visi juta, ka aiz zvaigžņu kustības "
        "pastāv apslēpta kārtība. Laika gaitā šie meklējumi kļuva par zinātni, filozofiju "
        "un tehnoloģiju."
    ),
    "Estonian": (
        "Sajandeid jälgisid tsivilisatsioonid taevast, otsides vastuseid. Mõned nägid "
        "jumalaid; teised vaid taevakehi. Ometi jagasid kõik aimdust, et tähtede liikumise "
        "taga on varjatud kord. Aja jooksul muutus see otsing teaduseks, filosoofiaks ja tehnoloogiaks."
    ),
    "Catalan": (
        "Durant segles, les civilitzacions van observar el cel buscant respostes. "
        "Alguns hi veien deus; d'altres, simples cossos celestes. Tanmateix, tots "
        "compartien la intuicio que existia un ordre ocult darrere el moviment de les estrelles. "
        "Amb el pas del temps, aquella recerca es va convertir en ciencia, filosofia i tecnologia."
    ),
    "Basque": (
        "Mendeetan zehar, zibilizazioek zerua behatu zuten erantzunak bilatuz. Batzuek "
        "jainkoak ikusten zituzten; beste batzuek, zeruko gorputz soilak. Hala ere, guztiek "
        "sentitzen zuten izarren mugimenduaren atzean ezkutuko ordena bat zegoela. Denborarekin, "
        "bilaketa hori zientzia, filosofia eta teknologia bihurtu zen."
    ),
    "Galician": (
        "Durante séculos, as civilizacións observaron o ceo buscando respostas. Algúns "
        "vían deuses; outros, simples corpos celestes. Porén, todos compartían a intuición "
        "de que existía unha orde oculta detrás do movemento das estrelas. Co paso do tempo, "
        "esa busca converteuse en ciencia, filosofía e tamén en tecnoloxía."
    ),
    "Welsh": (
        "Am ganrifoedd, bu gwareiddiadau yn arsylwi ar yr awyr gan chwilio am atebion. "
        "Gwelodd rhai dduwiau; gwelodd eraill gyrff nefol syml. Eto roedd pawb yn rhannu'r "
        "teimlad bod trefn gudd y tu ôl i symudiad y sêr. Dros amser, trodd y chwilio hwnnw "
        "yn wyddoniaeth, athroniaeth a hefyd dechnoleg."
    ),
    "Afrikaans": (
        "Vir eeue het beskawings na die hemel gekyk op soek na antwoorde. Sommige het "
        "gode gesien; ander net eenvoudige hemelliggame. Tog het almal die aanvoeling gedeel "
        "dat daar 'n verborge orde agter die beweging van die sterre bestaan. Met verloop van "
        "tyd het daardie soektog wetenskap, filosofie en ook tegnologie geword."
    ),
    "Amharic": (
        "ለዘመናት ሥልጣኔዎች መልሶችን በመፈለግ ሰማዩን ተመልክተዋል። አንዳንዶች አማልክትን "
        "አዩ፤ ሌሎች ግን ቀላል የሰማይ አካላትን ብቻ አዩ። ሆኖም ሁሉም ከከዋክብት እንቅስቃሴ "
        "በስተጀርባ የተሰወረ ሥርዓት እንዳለ ያለውን ግምት ተጋርተዋል። ጊዜ እያለፈ ሲሄድ "
        "ያ ፍለጋ ሳይንስ፣ ፍልስፍና እና ቴክኖሎጂ ሆነ።"
    ),
}


EDGE_VOICES = {
    "English": [
        _edge("en-US-AnaNeural", "Ana (Female, US child)", "English", "en-US", "Female"),
        _edge("en-US-AriaNeural", "Aria (Female, US)", "English", "en-US", "Female"),
        _edge("en-US-AvaNeural", "Ava (Female, US)", "English", "en-US", "Female"),
        _edge("en-US-ChristopherNeural", "Christopher (Male, US)", "English", "en-US", "Male"),
        _edge("en-US-EricNeural", "Eric (Male, US)", "English", "en-US", "Male"),
        _edge("en-US-GuyNeural", "Guy (Male, US)", "English", "en-US", "Male"),
        _edge("en-US-JennyNeural", "Jenny (Female, US)", "English", "en-US", "Female"),
        _edge("en-US-MichelleNeural", "Michelle (Female, US)", "English", "en-US", "Female"),
        _edge("en-US-RogerNeural", "Roger (Male, US)", "English", "en-US", "Male"),
        _edge("en-US-SteffanNeural", "Steffan (Male, US)", "English", "en-US", "Male"),
        _edge("en-GB-LibbyNeural", "Libby (Female, UK)", "English", "en-GB", "Female"),
        _edge("en-GB-MaisieNeural", "Maisie (Female, UK child)", "English", "en-GB", "Female"),
        _edge("en-GB-RyanNeural", "Ryan (Male, UK)", "English", "en-GB", "Male"),
        _edge("en-GB-SoniaNeural", "Sonia (Female, UK)", "English", "en-GB", "Female"),
        _edge("en-GB-ThomasNeural", "Thomas (Male, UK)", "English", "en-GB", "Male"),
        _edge("en-AU-NatashaNeural", "Natasha (Female, Australia)", "English", "en-AU", "Female"),
        _edge("en-AU-WilliamNeural", "William (Male, Australia)", "English", "en-AU", "Male"),
        _edge("en-CA-ClaraNeural", "Clara (Female, Canada)", "English", "en-CA", "Female"),
        _edge("en-CA-LiamNeural", "Liam (Male, Canada)", "English", "en-CA", "Male"),
        _edge("en-IN-NeerjaNeural", "Neerja (Female, India)", "English", "en-IN", "Female"),
        _edge("en-IN-PrabhatNeural", "Prabhat (Male, India)", "English", "en-IN", "Male"),
        _edge("en-IE-ConnorNeural", "Connor (Male, Ireland)", "English", "en-IE", "Male"),
        _edge("en-IE-EmilyNeural", "Emily (Female, Ireland)", "English", "en-IE", "Female"),
        _edge("en-NZ-MitchellNeural", "Mitchell (Male, New Zealand)", "English", "en-NZ", "Male"),
        _edge("en-NZ-MollyNeural", "Molly (Female, New Zealand)", "English", "en-NZ", "Female"),
        _edge("en-ZA-LeahNeural", "Leah (Female, South Africa)", "English", "en-ZA", "Female"),
        _edge("en-ZA-LukeNeural", "Luke (Male, South Africa)", "English", "en-ZA", "Male"),
    ],
    "Spanish": [
        _edge("es-ES-AlvaroNeural", "Alvaro (Male, Spain)", "Spanish", "es-ES", "Male"),
        _edge("es-ES-ElviraNeural", "Elvira (Female, Spain)", "Spanish", "es-ES", "Female"),
        _edge("es-MX-DaliaNeural", "Dalia (Female, Mexico)", "Spanish", "es-MX", "Female"),
        _edge("es-MX-JorgeNeural", "Jorge (Male, Mexico)", "Spanish", "es-MX", "Male"),
        _edge("es-US-AlonsoNeural", "Alonso (Male, United States)", "Spanish", "es-US", "Male"),
        _edge("es-US-PalomaNeural", "Paloma (Female, United States)", "Spanish", "es-US", "Female"),
        _edge("es-AR-ElenaNeural", "Elena (Female, Argentina)", "Spanish", "es-AR", "Female"),
        _edge("es-AR-TomasNeural", "Tomas (Male, Argentina)", "Spanish", "es-AR", "Male"),
        _edge("es-BO-MarceloNeural", "Marcelo (Male, Bolivia)", "Spanish", "es-BO", "Male"),
        _edge("es-BO-SofiaNeural", "Sofia (Female, Bolivia)", "Spanish", "es-BO", "Female"),
        _edge("es-CL-CatalinaNeural", "Catalina (Female, Chile)", "Spanish", "es-CL", "Female"),
        _edge("es-CL-LorenzoNeural", "Lorenzo (Male, Chile)", "Spanish", "es-CL", "Male"),
        _edge("es-CO-GonzaloNeural", "Gonzalo (Male, Colombia)", "Spanish", "es-CO", "Male"),
        _edge("es-CO-SalomeNeural", "Salome (Female, Colombia)", "Spanish", "es-CO", "Female"),
        _edge("es-CR-JuanNeural", "Juan (Male, Costa Rica)", "Spanish", "es-CR", "Male"),
        _edge("es-CR-MariaNeural", "Maria (Female, Costa Rica)", "Spanish", "es-CR", "Female"),
        _edge("es-CU-BelkysNeural", "Belkys (Female, Cuba)", "Spanish", "es-CU", "Female"),
        _edge("es-CU-ManuelNeural", "Manuel (Male, Cuba)", "Spanish", "es-CU", "Male"),
        _edge("es-DO-EmilioNeural", "Emilio (Male, Dominican Republic)", "Spanish", "es-DO", "Male"),
        _edge("es-DO-RamonaNeural", "Ramona (Female, Dominican Republic)", "Spanish", "es-DO", "Female"),
        _edge("es-EC-AndreaNeural", "Andrea (Female, Ecuador)", "Spanish", "es-EC", "Female"),
        _edge("es-EC-LuisNeural", "Luis (Male, Ecuador)", "Spanish", "es-EC", "Male"),
        _edge("es-GQ-JavierNeural", "Javier (Male, Equatorial Guinea)", "Spanish", "es-GQ", "Male"),
        _edge("es-GQ-TeresaNeural", "Teresa (Female, Equatorial Guinea)", "Spanish", "es-GQ", "Female"),
        _edge("es-GT-AndresNeural", "Andres (Male, Guatemala)", "Spanish", "es-GT", "Male"),
        _edge("es-GT-MartaNeural", "Marta (Female, Guatemala)", "Spanish", "es-GT", "Female"),
        _edge("es-HN-CarlosNeural", "Carlos (Male, Honduras)", "Spanish", "es-HN", "Male"),
        _edge("es-HN-KarlaNeural", "Karla (Female, Honduras)", "Spanish", "es-HN", "Female"),
        _edge("es-NI-FedericoNeural", "Federico (Male, Nicaragua)", "Spanish", "es-NI", "Male"),
        _edge("es-NI-YolandaNeural", "Yolanda (Female, Nicaragua)", "Spanish", "es-NI", "Female"),
        _edge("es-PA-MargaritaNeural", "Margarita (Female, Panama)", "Spanish", "es-PA", "Female"),
        _edge("es-PA-RobertoNeural", "Roberto (Male, Panama)", "Spanish", "es-PA", "Male"),
        _edge("es-PE-AlexNeural", "Alex (Male, Peru)", "Spanish", "es-PE", "Male"),
        _edge("es-PE-CamilaNeural", "Camila (Female, Peru)", "Spanish", "es-PE", "Female"),
        _edge("es-PR-KarinaNeural", "Karina (Female, Puerto Rico)", "Spanish", "es-PR", "Female"),
        _edge("es-PR-VictorNeural", "Victor (Male, Puerto Rico)", "Spanish", "es-PR", "Male"),
        _edge("es-PY-MarioNeural", "Mario (Male, Paraguay)", "Spanish", "es-PY", "Male"),
        _edge("es-PY-TaniaNeural", "Tania (Female, Paraguay)", "Spanish", "es-PY", "Female"),
        _edge("es-SV-LorenaNeural", "Lorena (Female, El Salvador)", "Spanish", "es-SV", "Female"),
        _edge("es-SV-RodrigoNeural", "Rodrigo (Male, El Salvador)", "Spanish", "es-SV", "Male"),
        _edge("es-UY-MateoNeural", "Mateo (Male, Uruguay)", "Spanish", "es-UY", "Male"),
        _edge("es-UY-ValentinaNeural", "Valentina (Female, Uruguay)", "Spanish", "es-UY", "Female"),
        _edge("es-VE-PaolaNeural", "Paola (Female, Venezuela)", "Spanish", "es-VE", "Female"),
        _edge("es-VE-SebastianNeural", "Sebastian (Male, Venezuela)", "Spanish", "es-VE", "Male"),
    ],
    "French": [
        _edge("fr-FR-DeniseNeural", "Denise (Female, France)", "French", "fr-FR", "Female"),
        _edge("fr-FR-HenriNeural", "Henri (Male, France)", "French", "fr-FR", "Male"),
        _edge("fr-CA-SylvieNeural", "Sylvie (Female, Canada)", "French", "fr-CA", "Female"),
        _edge("fr-CA-JeanNeural", "Jean (Male, Canada)", "French", "fr-CA", "Male"),
        _edge("fr-BE-CharlineNeural", "Charline (Female, Belgium)", "French", "fr-BE", "Female"),
        _edge("fr-BE-GerardNeural", "Gerard (Male, Belgium)", "French", "fr-BE", "Male"),
        _edge("fr-CH-ArianeNeural", "Ariane (Female, Switzerland)", "French", "fr-CH", "Female"),
        _edge("fr-CH-FabriceNeural", "Fabrice (Male, Switzerland)", "French", "fr-CH", "Male"),
    ],
    "German": [
        _edge("de-DE-KatjaNeural", "Katja (Female, Germany)", "German", "de-DE", "Female"),
        _edge("de-DE-ConradNeural", "Conrad (Male, Germany)", "German", "de-DE", "Male"),
        _edge("de-AT-IngridNeural", "Ingrid (Female, Austria)", "German", "de-AT", "Female"),
        _edge("de-AT-JonasNeural", "Jonas (Male, Austria)", "German", "de-AT", "Male"),
        _edge("de-CH-LeniNeural", "Leni (Female, Switzerland)", "German", "de-CH", "Female"),
        _edge("de-CH-JanNeural", "Jan (Male, Switzerland)", "German", "de-CH", "Male"),
    ],
    "Portuguese": [
        _edge("pt-BR-FranciscaNeural", "Francisca (Female, Brazil)", "Portuguese", "pt-BR", "Female"),
        _edge("pt-BR-AntonioNeural", "Antonio (Male, Brazil)", "Portuguese", "pt-BR", "Male"),
        _edge("pt-PT-RaquelNeural", "Raquel (Female, Portugal)", "Portuguese", "pt-PT", "Female"),
        _edge("pt-PT-DuarteNeural", "Duarte (Male, Portugal)", "Portuguese", "pt-PT", "Male"),
    ],
    "Italian": [
        _edge("it-IT-ElsaNeural", "Elsa (Female, Italy)", "Italian", "it-IT", "Female"),
        _edge("it-IT-IsabellaNeural", "Isabella (Female, Italy)", "Italian", "it-IT", "Female"),
        _edge("it-IT-DiegoNeural", "Diego (Male, Italy)", "Italian", "it-IT", "Male"),
    ],
    "Japanese": [
        _edge("ja-JP-NanamiNeural", "Nanami (Female, Japan)", "Japanese", "ja-JP", "Female"),
        _edge("ja-JP-KeitaNeural", "Keita (Male, Japan)", "Japanese", "ja-JP", "Male"),
    ],
    "Chinese": [
        _edge("zh-CN-XiaoxiaoNeural", "Xiaoxiao (Female, Mainland China)", "Chinese", "zh-CN", "Female"),
        _edge("zh-CN-XiaoyiNeural", "Xiaoyi (Female, Mainland China)", "Chinese", "zh-CN", "Female"),
        _edge("zh-CN-YunjianNeural", "Yunjian (Male, Mainland China)", "Chinese", "zh-CN", "Male"),
        _edge("zh-CN-YunxiNeural", "Yunxi (Male, Mainland China)", "Chinese", "zh-CN", "Male"),
        _edge("zh-CN-YunxiaNeural", "Yunxia (Male, Mainland China)", "Chinese", "zh-CN", "Male"),
        _edge("zh-CN-YunyangNeural", "Yunyang (Male, Mainland China)", "Chinese", "zh-CN", "Male"),
        _edge("zh-HK-HiuGaaiNeural", "HiuGaai (Female, Hong Kong)", "Chinese", "zh-HK", "Female"),
        _edge("zh-HK-HiuMaanNeural", "HiuMaan (Female, Hong Kong)", "Chinese", "zh-HK", "Female"),
        _edge("zh-HK-WanLungNeural", "WanLung (Male, Hong Kong)", "Chinese", "zh-HK", "Male"),
        _edge("zh-TW-HsiaoChenNeural", "HsiaoChen (Female, Taiwan)", "Chinese", "zh-TW", "Female"),
        _edge("zh-TW-HsiaoYuNeural", "HsiaoYu (Female, Taiwan)", "Chinese", "zh-TW", "Female"),
        _edge("zh-TW-YunJheNeural", "YunJhe (Male, Taiwan)", "Chinese", "zh-TW", "Male"),
    ],
    "Russian": [
        _edge("ru-RU-SvetlanaNeural", "Svetlana (Female, Russia)", "Russian", "ru-RU", "Female"),
        _edge("ru-RU-DmitryNeural", "Dmitry (Male, Russia)", "Russian", "ru-RU", "Male"),
    ],
    "Arabic": [
        _edge("ar-SA-ZariyahNeural", "Zariyah (Female, Saudi Arabia)", "Arabic", "ar-SA", "Female"),
        _edge("ar-SA-HamedNeural", "Hamed (Male, Saudi Arabia)", "Arabic", "ar-SA", "Male"),
        _edge("ar-EG-SalmaNeural", "Salma (Female, Egypt)", "Arabic", "ar-EG", "Female"),
        _edge("ar-EG-ShakirNeural", "Shakir (Male, Egypt)", "Arabic", "ar-EG", "Male"),
        _edge("ar-AE-FatimaNeural", "Fatima (Female, UAE)", "Arabic", "ar-AE", "Female"),
        _edge("ar-AE-HamdanNeural", "Hamdan (Male, UAE)", "Arabic", "ar-AE", "Male"),
        _edge("ar-BH-LailaNeural", "Laila (Female, Bahrain)", "Arabic", "ar-BH", "Female"),
        _edge("ar-BH-AliNeural", "Ali (Male, Bahrain)", "Arabic", "ar-BH", "Male"),
        _edge("ar-DZ-AminaNeural", "Amina (Female, Algeria)", "Arabic", "ar-DZ", "Female"),
        _edge("ar-DZ-IsmaelNeural", "Ismael (Male, Algeria)", "Arabic", "ar-DZ", "Male"),
        _edge("ar-IQ-RanaNeural", "Rana (Female, Iraq)", "Arabic", "ar-IQ", "Female"),
        _edge("ar-IQ-BasselNeural", "Bassel (Male, Iraq)", "Arabic", "ar-IQ", "Male"),
        _edge("ar-JO-SanaNeural", "Sana (Female, Jordan)", "Arabic", "ar-JO", "Female"),
        _edge("ar-JO-TaimNeural", "Taim (Male, Jordan)", "Arabic", "ar-JO", "Male"),
        _edge("ar-KW-NouraNeural", "Noura (Female, Kuwait)", "Arabic", "ar-KW", "Female"),
        _edge("ar-KW-FahedNeural", "Fahed (Male, Kuwait)", "Arabic", "ar-KW", "Male"),
        _edge("ar-LB-LaylaNeural", "Layla (Female, Lebanon)", "Arabic", "ar-LB", "Female"),
        _edge("ar-LB-RamiNeural", "Rami (Male, Lebanon)", "Arabic", "ar-LB", "Male"),
        _edge("ar-MA-MounaNeural", "Mouna (Female, Morocco)", "Arabic", "ar-MA", "Female"),
        _edge("ar-MA-JamalNeural", "Jamal (Male, Morocco)", "Arabic", "ar-MA", "Male"),
        _edge("ar-QA-AmalNeural", "Amal (Female, Qatar)", "Arabic", "ar-QA", "Female"),
        _edge("ar-QA-MoazNeural", "Moaz (Male, Qatar)", "Arabic", "ar-QA", "Male"),
        _edge("ar-SY-AmanyNeural", "Amany (Female, Syria)", "Arabic", "ar-SY", "Female"),
        _edge("ar-SY-LaithNeural", "Laith (Male, Syria)", "Arabic", "ar-SY", "Male"),
        _edge("ar-TN-ReemNeural", "Reem (Female, Tunisia)", "Arabic", "ar-TN", "Female"),
        _edge("ar-TN-HediNeural", "Hedi (Male, Tunisia)", "Arabic", "ar-TN", "Male"),
    ],
    "Korean": [
        _edge("ko-KR-SunHiNeural", "SunHi (Female, Korea)", "Korean", "ko-KR", "Female"),
        _edge("ko-KR-InJoonNeural", "InJoon (Male, Korea)", "Korean", "ko-KR", "Male"),
    ],
    "Hindi": [
        _edge("hi-IN-SwaraNeural", "Swara (Female, India)", "Hindi", "hi-IN", "Female"),
        _edge("hi-IN-MadhurNeural", "Madhur (Male, India)", "Hindi", "hi-IN", "Male"),
    ],
    "Dutch": [
        _edge("nl-NL-ColetteNeural", "Colette (Female, Netherlands)", "Dutch", "nl-NL", "Female"),
        _edge("nl-NL-FennaNeural", "Fenna (Female, Netherlands)", "Dutch", "nl-NL", "Female"),
        _edge("nl-NL-MaartenNeural", "Maarten (Male, Netherlands)", "Dutch", "nl-NL", "Male"),
        _edge("nl-BE-DenaNeural", "Dena (Female, Belgium)", "Dutch", "nl-BE", "Female"),
        _edge("nl-BE-ArnaudNeural", "Arnaud (Male, Belgium)", "Dutch", "nl-BE", "Male"),
    ],
    "Polish": [
        _edge("pl-PL-ZofiaNeural", "Zofia (Female, Poland)", "Polish", "pl-PL", "Female"),
        _edge("pl-PL-MarekNeural", "Marek (Male, Poland)", "Polish", "pl-PL", "Male"),
    ],
    "Turkish": [
        _edge("tr-TR-EmelNeural", "Emel (Female, Turkiye)", "Turkish", "tr-TR", "Female"),
        _edge("tr-TR-AhmetNeural", "Ahmet (Male, Turkiye)", "Turkish", "tr-TR", "Male"),
    ],
    "Ukrainian": [
        _edge("uk-UA-PolinaNeural", "Polina (Female, Ukraine)", "Ukrainian", "uk-UA", "Female"),
        _edge("uk-UA-OstapNeural", "Ostap (Male, Ukraine)", "Ukrainian", "uk-UA", "Male"),
    ],
    "Greek": [
        _edge("el-GR-AthinaNeural", "Athina (Female, Greece)", "Greek", "el-GR", "Female"),
        _edge("el-GR-NestorasNeural", "Nestoras (Male, Greece)", "Greek", "el-GR", "Male"),
    ],
    "Swedish": [
        _edge("sv-SE-SofieNeural", "Sofie (Female, Sweden)", "Swedish", "sv-SE", "Female"),
        _edge("sv-SE-MattiasNeural", "Mattias (Male, Sweden)", "Swedish", "sv-SE", "Male"),
    ],
    "Norwegian": [
        _edge("nb-NO-PernilleNeural", "Pernille (Female, Norway)", "Norwegian", "nb-NO", "Female"),
        _edge("nb-NO-FinnNeural", "Finn (Male, Norway)", "Norwegian", "nb-NO", "Male"),
    ],
    "Danish": [
        _edge("da-DK-ChristelNeural", "Christel (Female, Denmark)", "Danish", "da-DK", "Female"),
        _edge("da-DK-JeppeNeural", "Jeppe (Male, Denmark)", "Danish", "da-DK", "Male"),
    ],
    "Finnish": [
        _edge("fi-FI-NooraNeural", "Noora (Female, Finland)", "Finnish", "fi-FI", "Female"),
        _edge("fi-FI-HarriNeural", "Harri (Male, Finland)", "Finnish", "fi-FI", "Male"),
    ],
    "Czech": [
        _edge("cs-CZ-VlastaNeural", "Vlasta (Female, Czechia)", "Czech", "cs-CZ", "Female"),
        _edge("cs-CZ-AntoninNeural", "Antonin (Male, Czechia)", "Czech", "cs-CZ", "Male"),
    ],
    "Hungarian": [
        _edge("hu-HU-NoemiNeural", "Noemi (Female, Hungary)", "Hungarian", "hu-HU", "Female"),
        _edge("hu-HU-TamasNeural", "Tamas (Male, Hungary)", "Hungarian", "hu-HU", "Male"),
    ],
    "Romanian": [
        _edge("ro-RO-AlinaNeural", "Alina (Female, Romania)", "Romanian", "ro-RO", "Female"),
        _edge("ro-RO-EmilNeural", "Emil (Male, Romania)", "Romanian", "ro-RO", "Male"),
    ],
    "Thai": [
        _edge("th-TH-PremwadeeNeural", "Premwadee (Female, Thailand)", "Thai", "th-TH", "Female"),
        _edge("th-TH-NiwatNeural", "Niwat (Male, Thailand)", "Thai", "th-TH", "Male"),
    ],
    "Vietnamese": [
        _edge("vi-VN-HoaiMyNeural", "HoaiMy (Female, Vietnam)", "Vietnamese", "vi-VN", "Female"),
        _edge("vi-VN-NamMinhNeural", "NamMinh (Male, Vietnam)", "Vietnamese", "vi-VN", "Male"),
    ],
    "Indonesian": [
        _edge("id-ID-GadisNeural", "Gadis (Female, Indonesia)", "Indonesian", "id-ID", "Female"),
        _edge("id-ID-ArdiNeural", "Ardi (Male, Indonesia)", "Indonesian", "id-ID", "Male"),
    ],
    "Malay": [
        _edge("ms-MY-YasminNeural", "Yasmin (Female, Malaysia)", "Malay", "ms-MY", "Female"),
        _edge("ms-MY-OsmanNeural", "Osman (Male, Malaysia)", "Malay", "ms-MY", "Male"),
    ],
    "Hebrew": [
        _edge("he-IL-HilaNeural", "Hila (Female, Israel)", "Hebrew", "he-IL", "Female"),
        _edge("he-IL-AvriNeural", "Avri (Male, Israel)", "Hebrew", "he-IL", "Male"),
    ],
    "Bengali": [
        _edge("bn-BD-NabanitaNeural", "Nabanita (Female, Bangladesh)", "Bengali", "bn-BD", "Female"),
        _edge("bn-BD-PradeepNeural", "Pradeep (Male, Bangladesh)", "Bengali", "bn-BD", "Male"),
        _edge("bn-IN-TanishaaNeural", "Tanishaa (Female, India)", "Bengali", "bn-IN", "Female"),
        _edge("bn-IN-BashkarNeural", "Bashkar (Male, India)", "Bengali", "bn-IN", "Male"),
    ],
    "Urdu": [
        _edge("ur-PK-UzmaNeural", "Uzma (Female, Pakistan)", "Urdu", "ur-PK", "Female"),
        _edge("ur-PK-AsadNeural", "Asad (Male, Pakistan)", "Urdu", "ur-PK", "Male"),
        _edge("ur-IN-GulNeural", "Gul (Female, India)", "Urdu", "ur-IN", "Female"),
        _edge("ur-IN-SalmanNeural", "Salman (Male, India)", "Urdu", "ur-IN", "Male"),
    ],
    "Persian": [
        _edge("fa-IR-DilaraNeural", "Dilara (Female, Iran)", "Persian", "fa-IR", "Female"),
        _edge("fa-IR-FaridNeural", "Farid (Male, Iran)", "Persian", "fa-IR", "Male"),
    ],
    "Filipino": [
        _edge("fil-PH-BlessicaNeural", "Blessica (Female, Philippines)", "Filipino", "fil-PH", "Female"),
        _edge("fil-PH-AngeloNeural", "Angelo (Male, Philippines)", "Filipino", "fil-PH", "Male"),
    ],
    "Tamil": [
        _edge("ta-IN-PallaviNeural", "Pallavi (Female, India)", "Tamil", "ta-IN", "Female"),
        _edge("ta-IN-ValluvarNeural", "Valluvar (Male, India)", "Tamil", "ta-IN", "Male"),
        _edge("ta-LK-SaranyaNeural", "Saranya (Female, Sri Lanka)", "Tamil", "ta-LK", "Female"),
        _edge("ta-LK-KumarNeural", "Kumar (Male, Sri Lanka)", "Tamil", "ta-LK", "Male"),
        _edge("ta-MY-KaniNeural", "Kani (Female, Malaysia)", "Tamil", "ta-MY", "Female"),
        _edge("ta-MY-SuryaNeural", "Surya (Male, Malaysia)", "Tamil", "ta-MY", "Male"),
        _edge("ta-SG-VenbaNeural", "Venba (Female, Singapore)", "Tamil", "ta-SG", "Female"),
        _edge("ta-SG-AnbuNeural", "Anbu (Male, Singapore)", "Tamil", "ta-SG", "Male"),
    ],
    "Telugu": [
        _edge("te-IN-ShrutiNeural", "Shruti (Female, India)", "Telugu", "te-IN", "Female"),
        _edge("te-IN-MohanNeural", "Mohan (Male, India)", "Telugu", "te-IN", "Male"),
    ],
    "Marathi": [
        _edge("mr-IN-AarohiNeural", "Aarohi (Female, India)", "Marathi", "mr-IN", "Female"),
        _edge("mr-IN-ManoharNeural", "Manohar (Male, India)", "Marathi", "mr-IN", "Male"),
    ],
    "Gujarati": [
        _edge("gu-IN-DhwaniNeural", "Dhwani (Female, India)", "Gujarati", "gu-IN", "Female"),
        _edge("gu-IN-NiranjanNeural", "Niranjan (Male, India)", "Gujarati", "gu-IN", "Male"),
    ],
    "Kannada": [
        _edge("kn-IN-SapnaNeural", "Sapna (Female, India)", "Kannada", "kn-IN", "Female"),
        _edge("kn-IN-GaganNeural", "Gagan (Male, India)", "Kannada", "kn-IN", "Male"),
    ],
    "Malayalam": [
        _edge("ml-IN-SobhanaNeural", "Sobhana (Female, India)", "Malayalam", "ml-IN", "Female"),
        _edge("ml-IN-MidhunNeural", "Midhun (Male, India)", "Malayalam", "ml-IN", "Male"),
    ],
    "Swahili": [
        _edge("sw-KE-ZuriNeural", "Zuri (Female, Kenya)", "Swahili", "sw-KE", "Female"),
        _edge("sw-KE-RafikiNeural", "Rafiki (Male, Kenya)", "Swahili", "sw-KE", "Male"),
        _edge("sw-TZ-RehemaNeural", "Rehema (Female, Tanzania)", "Swahili", "sw-TZ", "Female"),
        _edge("sw-TZ-DaudiNeural", "Daudi (Male, Tanzania)", "Swahili", "sw-TZ", "Male"),
    ],
    "Burmese": [
        _edge("my-MM-NilarNeural", "Nilar (Female, Myanmar)", "Burmese", "my-MM", "Female"),
        _edge("my-MM-ThihaNeural", "Thiha (Male, Myanmar)", "Burmese", "my-MM", "Male"),
    ],
    "Javanese": [
        _edge("jv-ID-SitiNeural", "Siti (Female, Indonesia)", "Javanese", "jv-ID", "Female"),
        _edge("jv-ID-DimasNeural", "Dimas (Male, Indonesia)", "Javanese", "jv-ID", "Male"),
    ],
    "Punjabi": [
        _edge("pa-IN-GurpreetNeural", "Gurpreet (Female, India)", "Punjabi", "pa-IN", "Female"),
        _edge("pa-IN-OjasNeural", "Ojas (Male, India)", "Punjabi", "pa-IN", "Male"),
    ],
    "Nepali": [
        _edge("ne-NP-HemkalaNeural", "Hemkala (Female, Nepal)", "Nepali", "ne-NP", "Female"),
        _edge("ne-NP-SagarNeural", "Sagar (Male, Nepal)", "Nepali", "ne-NP", "Male"),
    ],
    "Zulu": [
        _edge("zu-ZA-ThandoNeural", "Thando (Female, South Africa)", "Zulu", "zu-ZA", "Female"),
        _edge("zu-ZA-ThembaNeural", "Themba (Male, South Africa)", "Zulu", "zu-ZA", "Male"),
    ],
    "Bulgarian": [
        _edge("bg-BG-KalinaNeural", "Kalina (Female, Bulgaria)", "Bulgarian", "bg-BG", "Female"),
        _edge("bg-BG-BorislavNeural", "Borislav (Male, Bulgaria)", "Bulgarian", "bg-BG", "Male"),
    ],
    "Croatian": [
        _edge("hr-HR-GabrijelaNeural", "Gabrijela (Female, Croatia)", "Croatian", "hr-HR", "Female"),
        _edge("hr-HR-SreckoNeural", "Srecko (Male, Croatia)", "Croatian", "hr-HR", "Male"),
    ],
    "Serbian": [
        _edge("sr-RS-SophieNeural", "Sophie (Female, Serbian Cyrillic)", "Serbian", "sr-RS", "Female"),
        _edge("sr-RS-NicholasNeural", "Nicholas (Male, Serbian Cyrillic)", "Serbian", "sr-RS", "Male"),
        _edge("sr-Latn-RS-SophieNeural", "Sophie (Female, Serbian Latin)", "Serbian", "sr-Latn-RS", "Female"),
        _edge("sr-Latn-RS-NicholasNeural", "Nicholas (Male, Serbian Latin)", "Serbian", "sr-Latn-RS", "Male"),
    ],
    "Slovak": [
        _edge("sk-SK-ViktoriaNeural", "Viktoria (Female, Slovakia)", "Slovak", "sk-SK", "Female"),
        _edge("sk-SK-LukasNeural", "Lukas (Male, Slovakia)", "Slovak", "sk-SK", "Male"),
    ],
    "Slovenian": [
        _edge("sl-SI-PetraNeural", "Petra (Female, Slovenia)", "Slovenian", "sl-SI", "Female"),
        _edge("sl-SI-RokNeural", "Rok (Male, Slovenia)", "Slovenian", "sl-SI", "Male"),
    ],
    "Lithuanian": [
        _edge("lt-LT-OnaNeural", "Ona (Female, Lithuania)", "Lithuanian", "lt-LT", "Female"),
        _edge("lt-LT-LeonasNeural", "Leonas (Male, Lithuania)", "Lithuanian", "lt-LT", "Male"),
    ],
    "Latvian": [
        _edge("lv-LV-EveritaNeural", "Everita (Female, Latvia)", "Latvian", "lv-LV", "Female"),
        _edge("lv-LV-NilsNeural", "Nils (Male, Latvia)", "Latvian", "lv-LV", "Male"),
    ],
    "Estonian": [
        _edge("et-EE-AnuNeural", "Anu (Female, Estonia)", "Estonian", "et-EE", "Female"),
        _edge("et-EE-KertNeural", "Kert (Male, Estonia)", "Estonian", "et-EE", "Male"),
    ],
    "Catalan": [
        _edge("ca-ES-JoanaNeural", "Joana (Female, Catalan)", "Catalan", "ca-ES", "Female"),
        _edge("ca-ES-EnricNeural", "Enric (Male, Catalan)", "Catalan", "ca-ES", "Male"),
    ],
    "Basque": [
        _edge("eu-ES-AinhoaNeural", "Ainhoa (Female, Basque)", "Basque", "eu-ES", "Female"),
        _edge("eu-ES-AnderNeural", "Ander (Male, Basque)", "Basque", "eu-ES", "Male"),
    ],
    "Galician": [
        _edge("gl-ES-SabelaNeural", "Sabela (Female, Galician)", "Galician", "gl-ES", "Female"),
        _edge("gl-ES-RoiNeural", "Roi (Male, Galician)", "Galician", "gl-ES", "Male"),
    ],
    "Welsh": [
        _edge("cy-GB-NiaNeural", "Nia (Female, Wales)", "Welsh", "cy-GB", "Female"),
        _edge("cy-GB-AledNeural", "Aled (Male, Wales)", "Welsh", "cy-GB", "Male"),
    ],
    "Afrikaans": [
        _edge("af-ZA-AdriNeural", "Adri (Female, South Africa)", "Afrikaans", "af-ZA", "Female"),
        _edge("af-ZA-WillemNeural", "Willem (Male, South Africa)", "Afrikaans", "af-ZA", "Male"),
    ],
    "Amharic": [
        _edge("am-ET-MekdesNeural", "Mekdes (Female, Ethiopia)", "Amharic", "am-ET", "Female"),
        _edge("am-ET-AmehaNeural", "Ameha (Male, Ethiopia)", "Amharic", "am-ET", "Male"),
    ],
}


KOKORO_VOICES = {
    "English": [
        _offline("af_heart", "Heart (Female)", "English", "en-US", "Female", "kokoro"),
        _offline("am_adam", "Adam (Male)", "English", "en-US", "Male", "kokoro"),
    ],
    "Spanish": [
        _offline("es_alex", "Alex (Male)", "Spanish", "es-ES", "Male", "kokoro"),
        _offline("es_elena", "Elena (Female)", "Spanish", "es-ES", "Female", "kokoro"),
    ],
}


PIPER_VOICES = {
    "English": [
        _offline("en_US-libritts-high", "LibriTTS (High Quality)", "English", "en-US", "Male", "piper"),
        _offline("en_GB-southern_english_female-low", "Southern (Female, Low)", "English", "en-GB", "Female", "piper"),
    ],
    "Spanish": [
        _offline("es_ES-carlfm-medium", "Carl (Male, Spain)", "Spanish", "es-ES", "Male", "piper"),
    ],
}


def kokoro_model_dir() -> Path:
    from audiobook_gen.paths import user_data_dir
    path = user_data_dir() / "models" / "kokoro"
    path.mkdir(parents=True, exist_ok=True)
    return path


def piper_model_dir() -> Path:
    from audiobook_gen.paths import user_data_dir
    path = user_data_dir() / "models" / "piper"
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_kokoro_installed() -> bool:
    model_dir = kokoro_model_dir()
    return (model_dir / "kokoro-v1.0.onnx").exists() and (model_dir / "voices-v1.0.bin").exists()


def is_piper_voice_installed(voice_id: str) -> bool:
    model_dir = piper_model_dir()
    return (model_dir / f"{voice_id}.onnx").exists() and (model_dir / f"{voice_id}.onnx.json").exists()


def get_installed_piper_voices() -> list[str]:
    return [file.stem for file in piper_model_dir().glob("*.onnx")]
