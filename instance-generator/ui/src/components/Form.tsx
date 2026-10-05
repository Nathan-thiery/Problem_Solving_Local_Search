import { useState } from 'react';
import {
  Box,
  Paper,
  Stack,
  Typography,
  Slider,
  RadioGroup,
  FormControlLabel,
  Radio,
  FormControl,
  FormLabel,
  Tooltip,
  IconButton,
  Button,
} from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { useCreateInstance } from './Api';

type instanceParams = {
  videosNb: number,
  cacheServersNb: number,
  endpointsNb: number,
  requestNb: number,
  videoDistribution: number,
  density: number,
  cacheSaturation: number,
  latencyDistribution: number
}

const SLIDER_CONFIG = {
  videos: {
    min: 10,
    max: 10000,
    step: 10,
    marks: [0, 2500, 5000, 7500, 10000].map((v) => ({ value: v, label: v.toLocaleString('fr-FR') })),
  },
  caches: {
    min: 1,
    max: 100,
    step: 1,
    marks: [0, 25, 50, 75, 100].map((v) => ({ value: v, label: `${v}` })),
  },
  endpoints: {
    min: 1,
    max: 500,
    step: 5,
    marks: [0, 125, 250, 375, 500].map((v) => ({ value: v, label: `${v}` })),
  },
  requetes: {
    min: 1,
    max: 100000,
    step: 100,
    marks: [0, 25000, 50000, 75000, 100000].map((v) => ({ value: v, label: v.toLocaleString('fr-FR') })),
  },
  densite: {
    min: 0,
    max: 100,
    step: 5,
    marks: [0, 25, 50, 75, 100].map((v) => ({ value: v, label: `${v}%` })),
  },
  pourcentage: {
    min: 1,
    max: 100,
    step: 1,
    marks: [1, 25, 50, 75, 100].map((v) => ({ value: v, label: `${v}%` })),
  },
};

type SliderMark = { value: number; label: string };
type SliderConfig = { min: number; max: number; step: number; marks: SliderMark[] };

type LabeledSliderProps = {
  label: string;
  tooltip: string;
  value: number;
  onChange: (value: number) => void;
  config: SliderConfig;
  suffix?: string;
};

function LabeledSlider({ label, tooltip, value, onChange, config, suffix = '' }: LabeledSliderProps) {
  return (
    <Box>
      <Typography variant="body2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        {label} : <strong>{value.toLocaleString('fr-FR')}{suffix}</strong>
        <Tooltip title={tooltip} arrow>
          <IconButton aria-label={`Informations sur ${label}`} size="small" sx={{ color: '#ffffff', padding: 0.25 }}>
            <InfoOutlinedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Typography>
      <Slider
        value={value}
        onChange={(_e, v) => onChange(Array.isArray(v) ? v[0] : v)}
        min={config.min}
        max={config.max}
        step={config.step}
        marks={config.marks}
        valueLabelDisplay="auto"
        sx={{
          '& .MuiSlider-markLabel': {
            fontSize: '0.7rem',
            color: '#9aa4ab',
          },
          '& .MuiSlider-mark': {
            backgroundColor: '#9aa4ab',
            height: 6,
          },
        }}
      />
    </Box>
  );
}

export function Form() {
  const [nbVideos, setNbVideos] = useState(500);
  const [nbCaches, setNbCaches] = useState(10);
  const [nbEndpoints, setNbEndpoints] = useState(50);
  const [nbRequetes, setNbRequetes] = useState(1000);
  const [distribution, setDistribution] = useState('homogene');
  const [densite, setDensite] = useState(50);
  const [cacheSaturation, setCacheSaturation] = useState(50);
  const [latencyDistribution, setLatencyDistribution] = useState(50);
  const { execute, loading, error } = useCreateInstance();

  const handleSubmit = async () => {
    const instanceParams: instanceParams = {
      videosNb: nbVideos,
      cacheServersNb: nbCaches,
      endpointsNb: nbEndpoints,
      requestNb: nbRequetes,
      videoDistribution: distribution === 'homogene' ? 0 : 1,
      density: densite,
      cacheSaturation,
      latencyDistribution,
    };
    const instanceFile = await execute(instanceParams);
    const url = URL.createObjectURL(instanceFile);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${nbVideos}_${nbEndpoints}_${nbRequetes}_${nbCaches}.in`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Paper
      elevation={3}
      sx={{
        backgroundColor: '#202529',
        color: '#ffffff',
        padding: 3,
        borderRadius: 2,
        maxWidth: 760,
        width: '100%',
      }}
    >
      <Stack spacing={3}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
            columnGap: 4,
            rowGap: 3,
          }}
        >
          <LabeledSlider
            label="Nombre de vidéos"
            tooltip="Nombre total de vidéos. Limite du format : de 1 à 10 000 vidéos. Chaque taille générée est comprise entre 1 et 1 000 MB."
            value={nbVideos}
            onChange={setNbVideos}
            config={SLIDER_CONFIG.videos}
          />
          <LabeledSlider
            label="Nombre de caches"
            tooltip="Nombre de serveurs cache. Limite du format : de 1 à 1 000 caches. Chaque cache partage la capacité X indiquée dans le fichier généré."
            value={nbCaches}
            onChange={setNbCaches}
            config={SLIDER_CONFIG.caches}
          />
          <LabeledSlider
            label="Nombre d'endpoints"
            tooltip="Nombre de zones d'utilisateurs. Limite du format : de 1 à 1 000 endpoints. Les descriptions de requêtes sont réparties entre eux."
            value={nbEndpoints}
            onChange={setNbEndpoints}
            config={SLIDER_CONFIG.endpoints}
          />
          <LabeledSlider
            label="Nombre de requêtes"
            tooltip="Nombre de descriptions de requêtes générées. Limite du format : 1 000 000 au total et au maximum 10 000 descriptions par endpoint."
            value={nbRequetes}
            onChange={setNbRequetes}
            config={SLIDER_CONFIG.requetes}
          />
          <LabeledSlider
            label="Saturation globale des caches"
            tooltip="Pourcentage de la capacité maximale d'un cache (500 000 MB). Par exemple, 50 % produit une capacité X de 250 000 MB pour chaque cache."
            value={cacheSaturation}
            onChange={setCacheSaturation}
            config={SLIDER_CONFIG.pourcentage}
            suffix="%"
          />
          <LabeledSlider
            label="Variabilité des latences caches"
            tooltip="Contrôle la plage des latences entre les endpoints et les caches. Elles restent entre 1 et 500 ms et toujours inférieures à la latence du data center."
            value={latencyDistribution}
            onChange={setLatencyDistribution}
            config={SLIDER_CONFIG.pourcentage}
            suffix="%"
          />
        </Box>

        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
            columnGap: 4,
            rowGap: 3,
            alignItems: 'start',
          }}
        >
          <FormControl size="small">
            <FormLabel sx={{ color: '#ffffff', display: 'flex', alignItems: 'center', gap: 0.5, fontSize: '0.875rem' }}>
              Distribution de la demande des vidéos
              <Tooltip
                title="Homogène : toutes les vidéos sont demandées à peu près au même rythme. Hétérogène : quelques vidéos concentrent l'essentiel des demandes (effet de popularité, type Zipf), tandis que la majorité des vidéos sont peu sollicitées."
                arrow
              >
                <IconButton size="small" sx={{ color: '#ffffff', padding: 0.5 }}>
                  <InfoOutlinedIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </FormLabel>
            <RadioGroup
              row
              value={distribution}
              onChange={(e) => setDistribution(e.target.value)}
            >
              <FormControlLabel value="homogene" control={<Radio size="small" sx={{ color: '#ffffff' }} />} label="Homogène" />
              <FormControlLabel value="heterogene" control={<Radio size="small" sx={{ color: '#ffffff' }} />} label="Hétérogène" />
            </RadioGroup>
          </FormControl>

          <LabeledSlider
            label="Densité de connexion endpoints/caches"
            tooltip="Pourcentage de caches connectés à chaque endpoint. 0 % signifie aucune connexion ; 100 % connecte chaque endpoint à tous les caches."
            value={densite}
            onChange={setDensite}
            config={SLIDER_CONFIG.densite}
            suffix="%"
          />
        </Box>

        {error && <Typography color="error">{error.message}</Typography>}
        <Button variant="contained" onClick={handleSubmit} disabled={loading}>
          {loading ? 'Génération en cours...' : "Générer l'instance"}
        </Button>
      </Stack>
    </Paper>
  );
}
