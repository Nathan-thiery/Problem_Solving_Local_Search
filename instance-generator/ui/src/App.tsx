import { Box, Typography, CssBaseline } from '@mui/material';
import { Form } from './components/Form';

export function App() {
  return (
    <>
      <CssBaseline />
      <Box
        sx={{
          backgroundColor: '#202529',
          color: '#ffffff',
          minHeight: '100vh',
          width: '100vw',
          margin: 0,
          padding: 3,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Typography variant="h4" sx={{padding: '20px'}}>Instance Generator</Typography>

        <Form/>
      </Box>
    </>
  );
}